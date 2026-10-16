using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using System.Xml.Linq;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.AspNetCore.DataProtection.KeyManagement;
using Microsoft.AspNetCore.DataProtection.Repositories;
using Microsoft.AspNetCore.DataProtection.StackExchangeRedis;
using Microsoft.AspNetCore.DataProtection.XmlEncryption;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using StackExchange.Redis;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class DataProtectionKeyStartupExtensions
{
    private static readonly XNamespace DataProtectionNamespace = "http://schemas.asp.net/2015/03/dataProtection";
    private static readonly XName RequiresEncryption = DataProtectionNamespace + "requiresEncryption";
    private static readonly XName EncryptedSecret = DataProtectionNamespace + "encryptedSecret";

    public static async Task ImportAndValidateDataProtectionKeysAsync(this WebApplication app)
    {
        if (!app.Configuration.GetValue<bool>("Accounts:Enabled"))
        {
            return;
        }

        try
        {
            await ImportAndValidateAsync(app);
        }
        catch (Exception)
        {
            // Key XML contains secret material. Keep startup diagnostics useful without
            // forwarding XML, certificate details, connection data or crypto exceptions.
            throw new InvalidOperationException(
                "Data Protection key validation or legacy import failed; enabled accounts will not start.");
        }
    }

    private static async Task ImportAndValidateAsync(WebApplication app)
    {
        var settings = app.Configuration.GetSection(DataProtectionKeyStorageOptions.SectionName)
            .Get<DataProtectionKeyStorageOptions>() ?? new DataProtectionKeyStorageOptions();
        if (!settings.HasValidLegacySource())
        {
            throw new InvalidOperationException();
        }

        var appName = app.Configuration.GetValue<string>("App:Name");
        if (string.IsNullOrWhiteSpace(appName))
        {
            throw new InvalidOperationException();
        }

        var services = app.Services;
        var keyManagementOptions = services.GetRequiredService<IOptions<KeyManagementOptions>>().Value;
        var destination = keyManagementOptions.XmlRepository
            ?? throw new InvalidOperationException();
        var source = CreateLegacyRepository(settings, app.Environment, services);
        var sourceDocuments = source is null
            ? []
            : ReadDocuments(source.GetAllElements(), keyManagementOptions.XmlEncryptor);
        if (settings.LegacyKeyStore != "None" && sourceDocuments.Count == 0)
        {
            throw new InvalidOperationException();
        }

        await using var scope = services.CreateAsyncScope();
        var dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
        var lockId = GetImportLockId(appName);
        await using (var strategyDb = await dbFactory.CreateDbContextAsync())
        {
            var strategy = strategyDb.Database.CreateExecutionStrategy();
            await strategy.ExecuteAsync(async () =>
            {
                await using var db = await dbFactory.CreateDbContextAsync();
                await using var transaction = await db.Database.BeginTransactionAsync();
                await db.Database.ExecuteSqlInterpolatedAsync($"SELECT pg_advisory_xact_lock({lockId})");

                var rows = await db.DataProtectionKeys.ToListAsync();
                var destinationDocuments = PrepareExistingRows(rows, keyManagementOptions.XmlEncryptor);
                var byIdentity = BuildIdentityMap(destinationDocuments);

                foreach (var document in sourceDocuments)
                {
                    if (byIdentity.TryGetValue(document.Identity, out var existing))
                    {
                        if ((existing.IsKey && document.IsKey
                                && existing.SourceFingerprint == document.SourceFingerprint
                                && IsVerifiedImportedKey(existing))
                            || XNode.DeepEquals(existing.Element, document.StoredElement))
                        {
                            continue;
                        }

                        throw new InvalidOperationException();
                    }

                    // EntityFrameworkCoreXmlRepository.StoreElement creates its own DI scope
                    // and DbContext. Insert through this transaction so the advisory lock
                    // and the import rows commit atomically across app replicas.
                    db.DataProtectionKeys.Add(new Microsoft.AspNetCore.DataProtection.EntityFrameworkCore.DataProtectionKey
                    {
                        FriendlyName = document.FriendlyName,
                        Xml = document.StoredElement.ToString(SaveOptions.DisableFormatting)
                    });
                    byIdentity.Add(document.Identity, document);
                }

                await db.SaveChangesAsync();
                await transaction.CommitAsync();
            });
        }

        var persistedDocuments = ReadDocuments(destination.GetAllElements(), encryptor: null, requireProtection: true);
        var persistedByIdentity = BuildIdentityMap(persistedDocuments);
        foreach (var document in sourceDocuments)
        {
            if (!persistedByIdentity.ContainsKey(document.Identity))
            {
                throw new InvalidOperationException();
            }
        }

        var keys = services.GetRequiredService<IKeyManager>().GetAllKeys();
        var keysById = keys.ToDictionary(key => key.KeyId);
        foreach (var key in keys)
        {
            _ = key.CreateEncryptor();
        }

        foreach (var document in sourceDocuments.Where(document => document.KeyId.HasValue))
        {
            if (!keysById.ContainsKey(document.KeyId!.Value))
            {
                throw new InvalidOperationException();
            }
        }

        foreach (var revocation in sourceDocuments.Where(document => document.RevokedKeyId.HasValue))
        {
            if (!keysById.TryGetValue(revocation.RevokedKeyId!.Value, out var key) || !key.IsRevoked)
            {
                throw new InvalidOperationException();
            }
        }

        foreach (var revocation in sourceDocuments.Where(document => document.MassRevocationDate.HasValue))
        {
            if (keys.Any(key => key.CreationDate < revocation.MassRevocationDate && !key.IsRevoked))
            {
                throw new InvalidOperationException();
            }
        }
    }

    private static IXmlRepository? CreateLegacyRepository(
        DataProtectionKeyStorageOptions settings,
        IHostEnvironment environment,
        IServiceProvider services)
    {
        switch (settings.LegacyKeyStore)
        {
            case "None":
                return null;
            case "FileSystem":
                {
                    var path = Path.GetFullPath(settings.LegacyKeyStoragePath, environment.ContentRootPath);
                    if (!Directory.Exists(path) || (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
                    {
                        throw new InvalidOperationException();
                    }

                    return new FileSystemXmlRepository(new DirectoryInfo(path), services.GetRequiredService<ILoggerFactory>());
                }
            case "Redis":
                {
                    if (settings.LegacyRedisKey.Contains('\r') || settings.LegacyRedisKey.Contains('\n'))
                    {
                        throw new InvalidOperationException();
                    }

                    var redis = services.GetRequiredService<IConnectionMultiplexer>();
                    return new RedisXmlRepository(() => redis.GetDatabase(), (RedisKey)settings.LegacyRedisKey);
                }
            default:
                throw new InvalidOperationException();
        }
    }

    private static List<KeyDocument> ReadDocuments(
        IReadOnlyCollection<XElement> elements,
        IXmlEncryptor? encryptor,
        bool requireProtection = false)
    {
        List<KeyDocument> documents = [];
        Dictionary<string, KeyDocument> identities = new(StringComparer.Ordinal);
        foreach (var element in elements)
        {
            var original = new XElement(element);
            var document = Describe(original, encryptor, requireProtection);
            if (identities.TryGetValue(document.Identity, out var previous))
            {
                if (!XNode.DeepEquals(previous.OriginalElement, document.OriginalElement))
                {
                    throw new InvalidOperationException();
                }

                if (document.IsKey)
                {
                    throw new InvalidOperationException();
                }

                continue;
            }

            identities.Add(document.Identity, document);
            documents.Add(document);
        }

        return documents;
    }

    private static List<KeyDocument> PrepareExistingRows(
        IReadOnlyList<Microsoft.AspNetCore.DataProtection.EntityFrameworkCore.DataProtectionKey> rows,
        IXmlEncryptor? encryptor)
    {
        List<KeyDocument> documents = [];
        Dictionary<string, KeyDocument> identities = new(StringComparer.Ordinal);
        foreach (var row in rows)
        {
            if (string.IsNullOrWhiteSpace(row.Xml) || string.IsNullOrWhiteSpace(row.FriendlyName))
            {
                throw new InvalidOperationException();
            }

            var document = Describe(XElement.Parse(row.Xml), encryptor);
            if (identities.TryGetValue(document.Identity, out var previous))
            {
                if (!XNode.DeepEquals(previous.Element, document.StoredElement))
                {
                    throw new InvalidOperationException();
                }

                if (document.IsKey)
                {
                    throw new InvalidOperationException();
                }

                continue;
            }

            if (document.IsKey && document.OriginalElement.DescendantsAndSelf().Any(RequiresWrapping))
            {
                row.Xml = document.StoredElement.ToString(SaveOptions.DisableFormatting);
                row.FriendlyName = MakeImportedKeyName(
                    document.KeyId!.Value,
                    Fingerprint(document.OriginalElement),
                    Fingerprint(document.StoredElement));
            }

            var sourceFingerprint = Fingerprint(document.OriginalElement);
            if (document.IsKey && TryReadImportedKeyName(
                    row.FriendlyName,
                    document.KeyId!.Value,
                    Fingerprint(document.StoredElement),
                    out var importedFingerprint))
            {
                sourceFingerprint = importedFingerprint;
            }

            document = document with
            {
                FriendlyName = row.FriendlyName,
                SourceFingerprint = sourceFingerprint
            };
            identities.Add(document.Identity, document);
            documents.Add(document);
        }

        return documents;
    }

    private static Dictionary<string, KeyDocument> BuildIdentityMap(IEnumerable<KeyDocument> documents)
    {
        Dictionary<string, KeyDocument> result = new(StringComparer.Ordinal);
        foreach (var document in documents)
        {
            if (!result.TryAdd(document.Identity, document))
            {
                throw new InvalidOperationException();
            }
        }

        return result;
    }

    private static KeyDocument Describe(XElement original, IXmlEncryptor? encryptor, bool requireProtection = false)
    {
        if (original.Name == "key")
        {
            var keyId = (Guid?)original.Attribute("id") ?? throw new InvalidOperationException();
            _ = (DateTimeOffset?)original.Element("creationDate") ?? throw new InvalidOperationException();
            _ = (DateTimeOffset?)original.Element("activationDate") ?? throw new InvalidOperationException();
            _ = (DateTimeOffset?)original.Element("expirationDate") ?? throw new InvalidOperationException();
            if (original.Element("descriptor") is null)
            {
                throw new InvalidOperationException();
            }

            var fingerprint = Fingerprint(original);
            var stored = ProtectUnwrappedKey(original, encryptor);
            if (!stored.DescendantsAndSelf(EncryptedSecret).Any())
            {
                throw new InvalidOperationException();
            }

            if (requireProtection && stored.DescendantsAndSelf().Any(RequiresWrapping))
            {
                throw new InvalidOperationException();
            }

            return new KeyDocument(
                $"key:{keyId:D}",
                MakeImportedKeyName(keyId, fingerprint, Fingerprint(stored)),
                original,
                stored,
                keyId,
                null,
                null,
                IsKey: true,
                SourceFingerprint: fingerprint);
        }

        if (original.Name == "revocation")
        {
            var revocationDate = (DateTimeOffset?)original.Element("revocationDate")
                ?? throw new InvalidOperationException();
            var revokedId = (string?)original.Element("key")?.Attribute("id") ?? throw new InvalidOperationException();
            string identity;
            Guid? revokedKeyId = null;
            if (revokedId == "*")
            {
                identity = $"revocation:all:{revocationDate.UtcTicks}";
            }
            else
            {
                revokedKeyId = Guid.Parse(revokedId);
                identity = $"revocation:key:{revokedKeyId.Value:D}";
            }

            return new KeyDocument(
                identity,
                $"source-revocation-{Fingerprint(original)}",
                original,
                original,
                null,
                revokedKeyId,
                revokedId == "*" ? revocationDate : null,
                IsKey: false,
                SourceFingerprint: Fingerprint(original));
        }

        throw new InvalidOperationException();
    }

    private static XElement ProtectUnwrappedKey(XElement element, IXmlEncryptor? encryptor)
    {
        var copy = new XElement(element);
        while (copy.DescendantsAndSelf().FirstOrDefault(RequiresWrapping) is { } secret)
        {
            if (encryptor is null)
            {
                throw new InvalidOperationException();
            }

            var encrypted = encryptor.Encrypt(new XElement(secret));
            secret.ReplaceWith(new XElement(
                EncryptedSecret,
                new XAttribute("decryptorType", encrypted.DecryptorType.AssemblyQualifiedName
                    ?? throw new InvalidOperationException()),
                encrypted.EncryptedElement));
        }

        return copy;
    }

    private static bool RequiresWrapping(XElement element) =>
        (bool?)element.Attribute(RequiresEncryption) == true;

    private static string MakeImportedKeyName(Guid id, string sourceFingerprint, string storedFingerprint) =>
        $"source-key:{id:N}:{sourceFingerprint}:{storedFingerprint}";

    private static bool TryReadImportedKeyName(
        string friendlyName,
        Guid id,
        string storedFingerprint,
        out string sourceFingerprint)
    {
        sourceFingerprint = string.Empty;
        var pieces = friendlyName.Split(':');
        if (pieces.Length != 4
            || pieces[0] != "source-key"
            || !Guid.TryParseExact(pieces[1], "N", out var storedId)
            || storedId != id
            || pieces[2].Length != 64
            || pieces[3] != storedFingerprint
            || pieces[2].Any(character => !Uri.IsHexDigit(character)))
        {
            return false;
        }

        sourceFingerprint = pieces[2];
        return true;
    }

    private static bool IsVerifiedImportedKey(KeyDocument document)
    {
        return document.KeyId.HasValue
            && TryReadImportedKeyName(
                document.FriendlyName,
                document.KeyId.Value,
                Fingerprint(document.StoredElement),
                out var sourceFingerprint)
            && sourceFingerprint == document.SourceFingerprint;
    }

    private static string Fingerprint(XElement element) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(
            element.ToString(SaveOptions.DisableFormatting)))).ToLowerInvariant();

    private static long GetImportLockId(string appName)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes("BlazorAutoApp.DataProtection.LegacyImport\0" + appName));
        return BinaryPrimitives.ReadInt64BigEndian(hash);
    }

    private sealed record KeyDocument(
        string Identity,
        string FriendlyName,
        XElement OriginalElement,
        XElement StoredElement,
        Guid? KeyId,
        Guid? RevokedKeyId,
        DateTimeOffset? MassRevocationDate,
        bool IsKey,
        string SourceFingerprint)
    {
        public XElement Element => StoredElement;
    }
}
