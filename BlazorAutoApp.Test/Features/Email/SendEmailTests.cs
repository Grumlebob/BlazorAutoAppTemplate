using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;
using BlazorAutoApp.Client.Services;
using BlazorAutoApp.Core.Features.Email;
using Xunit;

namespace BlazorAutoApp.Test.Features.Email;

public class SendEmailTests
{
    [Fact]
    public async Task Send_Success202_WithPayload_ReturnsSuccessTrue()
    {
        // Arrange
        var expectedResponse = new SendEmailResponse { Success = true };
        var handler = new StubHttpMessageHandler(req =>
        {
            Assert.Equal(HttpMethod.Post, req.Method);
            Assert.Equal("http://localhost/api/email/send", req.RequestUri!.ToString());
            return new HttpResponseMessage(HttpStatusCode.Accepted)
            {
                Content = JsonContent.Create(expectedResponse)
            };
        });

        var client = new HttpClient(handler) { BaseAddress = new Uri("http://localhost") };
        var svc = new SendEmailClientService(client);

        // Act
        var result = await svc.SendAsync(new SendEmailRequest
        {
            To = "to@example.com",
            Subject = "Hello",
            Text = "Hi"
        });

        // Assert
        Assert.True(result.Success);
        Assert.Null(result.Error);
        var sentBody = await handler.ReadSentBodyAsync();
        Assert.Contains("\"To\":\"to@example.com\"", sentBody, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("\"Text\":\"Hi\"", sentBody, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Send_Success202_NoPayload_ReturnsSuccessTrue()
    {
        // Arrange
        var handler = new StubHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.Accepted)
            {
                // No JSON body (server could return empty content on 202)
                Content = new StringContent(string.Empty)
            });

        var client = new HttpClient(handler) { BaseAddress = new Uri("http://localhost") };
        var svc = new SendEmailClientService(client);

        // Act
        var result = await svc.SendAsync(new SendEmailRequest { To = "to@example.com" });

        // Assert
        Assert.True(result.Success);
        Assert.Null(result.Error);
    }

    [Fact]
    public async Task Send_BadRequest_TypedPayload_ReturnsTypedError()
    {
        // Arrange
        var serverPayload = new SendEmailResponse { Success = false, Error = "SendGrid 400" };
        var handler = new StubHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.BadRequest)
            {
                Content = JsonContent.Create(serverPayload)
            });

        var client = new HttpClient(handler) { BaseAddress = new Uri("http://localhost") };
        var svc = new SendEmailClientService(client);

        // Act
        var result = await svc.SendAsync(new SendEmailRequest { To = "to@example.com" });

        // Assert
        Assert.False(result.Success);
        Assert.Equal("SendGrid 400", result.Error);
    }

    [Fact]
    public async Task Send_BadRequest_TextBody_ReturnsTextError()
    {
        // Arrange
        const string errorText = "Missing 'To'";
        var handler = new StubHttpMessageHandler(_ =>
            new HttpResponseMessage(HttpStatusCode.BadRequest)
            {
                Content = new StringContent(errorText)
            });

        var client = new HttpClient(handler) { BaseAddress = new Uri("http://localhost") };
        var svc = new SendEmailClientService(client);

        // Act
        var result = await svc.SendAsync(new SendEmailRequest { To = "" });

        // Assert
        Assert.False(result.Success);
        Assert.Equal(errorText, result.Error);
    }

    [Fact]
    public async Task Send_PostsToCorrectRoute_WithJsonBody()
    {
        // Arrange
        var handler = new StubHttpMessageHandler(req =>
        {
            Assert.Equal("http://localhost/api/email/send", req.RequestUri!.ToString());
            Assert.Equal(HttpMethod.Post, req.Method);
            return new HttpResponseMessage(HttpStatusCode.Accepted)
            {
                Content = JsonContent.Create(new SendEmailResponse { Success = true })
            };
        });

        var client = new HttpClient(handler) { BaseAddress = new Uri("http://localhost") };
        var svc = new SendEmailClientService(client);

        // Act
        var req = new SendEmailRequest { To = "check@route.test", Subject = "Sub", Text = "Body" };
        var _ = await svc.SendAsync(req);

        // Assert
        var body = await handler.ReadSentBodyAsync();
        // basic sanity on serialized JSON
        Assert.Contains("\"To\":\"check@route.test\"", body, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("\"Subject\":\"Sub\"", body, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("\"Text\":\"Body\"", body, StringComparison.OrdinalIgnoreCase);
    }

    private sealed class StubHttpMessageHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _responder;
        public HttpRequestMessage? LastRequest { get; private set; }

        public StubHttpMessageHandler(Func<HttpRequestMessage, HttpResponseMessage> responder)
        {
            _responder = responder;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastRequest = request;
            return Task.FromResult(_responder(request));
        }

        public async Task<string> ReadSentBodyAsync()
        {
            if (LastRequest?.Content is null) return string.Empty;
            return await LastRequest.Content.ReadAsStringAsync();
        }
    }
}
