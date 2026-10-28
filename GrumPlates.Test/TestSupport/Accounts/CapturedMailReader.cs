using System;
using System.IO;
using MimeKit;

namespace GrumPlates.Test.TestSupport.Accounts;

internal static class CapturedMailReader
{
    public static MimeMessage? TryLoad(string path)
    {
        try
        {
            using var stream = File.OpenRead(path);
            return MimeMessage.Load(stream);
        }
        catch (IOException)
        {
            return null;
        }
        catch (FormatException)
        {
            return null;
        }
    }
}
