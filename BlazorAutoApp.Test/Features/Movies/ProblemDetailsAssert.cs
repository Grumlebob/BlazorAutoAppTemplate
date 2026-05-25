using System.Net.Http;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

internal static class ProblemDetailsAssert
{
    public static async Task<ProblemDetails> IsProblemAsync(HttpResponseMessage response, int statusCode, string title)
    {
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);

        var problem = await response.Content.ReadFromJsonAsync<ProblemDetails>();
        Assert.NotNull(problem);
        Assert.Equal(statusCode, problem!.Status);
        Assert.Equal(title, problem.Title);

        return problem;
    }

    public static async Task<HttpValidationProblemDetails> IsValidationProblemAsync(HttpResponseMessage response, params string[] expectedKeys)
    {
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);

        var problem = await response.Content.ReadFromJsonAsync<HttpValidationProblemDetails>();
        Assert.NotNull(problem);
        Assert.Equal(StatusCodes.Status400BadRequest, problem!.Status);

        foreach (var key in expectedKeys)
        {
            Assert.Contains(key, problem.Errors.Keys);
        }

        return problem;
    }
}
