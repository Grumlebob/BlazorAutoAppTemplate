namespace BlazorAutoApp.Simulation.Auth;

internal static class PlaywrightInstaller
{
    public static int InstallChromium()
    {
        Console.WriteLine("Installing Playwright Chromium browser...");
        var exitCode = Microsoft.Playwright.Program.Main(["install", "chromium"]);
        if (exitCode == 0)
        {
            Console.WriteLine("Playwright Chromium install ok.");
        }

        return exitCode;
    }
}
