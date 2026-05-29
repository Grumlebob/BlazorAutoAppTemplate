using System.Net;
using BlazorAutoApp.Infrastructure.Hosting;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Http;
using Serilog.Events;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

public sealed class ObservabilityTests
{
    [Theory]
    [InlineData("/health/live")]
    [InlineData("/health/ready")]
    [InlineData("/_framework/blazor.web.js")]
    [InlineData("/assets/app.css")]
    [InlineData("/favicon.ico")]
    [InlineData("/app.css")]
    public void RequestLogging_DowngradesHealthAndStaticRequests(string path)
    {
        var context = CreateContext(path, StatusCodes.Status200OK);

        var level = ObservabilityExtensions.GetRequestLogLevel(context, ex: null);

        Assert.Equal(LogEventLevel.Verbose, level);
    }

    [Fact]
    public void RequestLogging_KeepsApplicationRequestsAtInformation()
    {
        var context = CreateContext("/api/books", StatusCodes.Status200OK);

        var level = ObservabilityExtensions.GetRequestLogLevel(context, ex: null);

        Assert.Equal(LogEventLevel.Information, level);
    }

    [Fact]
    public void RequestLogging_KeepsErrorsAtError()
    {
        var context = CreateContext("/api/books", StatusCodes.Status500InternalServerError);

        var level = ObservabilityExtensions.GetRequestLogLevel(context, ex: null);

        Assert.Equal(LogEventLevel.Error, level);
    }

    [Fact]
    public async Task AppStarts_WhenOpenTelemetryIsDisabled()
    {
        await using var factory = new WebAppFactory(new WebAppFactoryOptions
        {
            OpenTelemetryEnabled = false
        });
        await factory.InitializeAsync();

        var response = await factory.HttpClient.GetAsync("/health/live");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task AppStarts_WhenOpenTelemetryEndpointIsMissing()
    {
        await using var factory = new WebAppFactory(new WebAppFactoryOptions
        {
            OpenTelemetryEnabled = true,
            OpenTelemetryEndpoint = "http://127.0.0.1:4317"
        });
        await factory.InitializeAsync();

        var response = await factory.HttpClient.GetAsync("/health/live");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    private static DefaultHttpContext CreateContext(string path, int statusCode)
    {
        var context = new DefaultHttpContext();
        context.Request.Path = path;
        context.Response.StatusCode = statusCode;
        return context;
    }
}
