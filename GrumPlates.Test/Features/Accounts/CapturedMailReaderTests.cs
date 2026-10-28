using System;
using System.IO;
using GrumPlates.Test.TestSupport.Accounts;
using MimeKit;
using Xunit;

namespace GrumPlates.Test.Features.Accounts;

public sealed class CapturedMailReaderTests
{
    [Fact]
    public void TryLoad_ReturnsNull_WhenCaptureIsIncomplete()
    {
        var path = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.eml");
        try
        {
            File.WriteAllBytes(path, Array.Empty<byte>());

            Assert.Null(CapturedMailReader.TryLoad(path));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void TryLoad_ParsesCompletedCapture()
    {
        var path = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid():N}.eml");
        var expected = new MimeMessage
        {
            Subject = "Account confirmation",
            Body = new TextPart("plain") { Text = "https://example.test/confirm" },
        };
        expected.From.Add(new MailboxAddress("Sender", "sender@example.test"));
        expected.To.Add(new MailboxAddress("Recipient", "recipient@example.test"));

        try
        {
            using (var stream = File.Create(path))
            {
                expected.WriteTo(stream);
            }

            var actual = CapturedMailReader.TryLoad(path);

            Assert.NotNull(actual);
            Assert.Equal(expected.Subject, actual.Subject);
            Assert.Equal(expected.TextBody, actual.TextBody?.TrimEnd('\r', '\n'));
            Assert.Equal("recipient@example.test", Assert.Single(actual.To.Mailboxes).Address);
        }
        finally
        {
            File.Delete(path);
        }
    }
}
