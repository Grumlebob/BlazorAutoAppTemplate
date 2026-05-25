using System.Net.Http.Json;
using System.Net;
using BlazorAutoApp.Core.Features.Movies.Contracts;
using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.DeleteMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;

namespace BlazorAutoApp.Client.Features.Movies;

public class MoviesClientService(HttpClient http) : IMoviesApi
{
    private readonly HttpClient _http = http;

    public async Task<GetMoviesResponse> GetAsync(GetMoviesRequest req, CancellationToken cancellationToken = default)
    {
        var res = await _http.GetFromJsonAsync<GetMoviesResponse>("api/movies", cancellationToken);
        return res ?? new GetMoviesResponse { Movies = [] };
    }

    public async Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req, CancellationToken cancellationToken = default)
    {
        using var res = await _http.GetAsync($"api/movies/{req.Id}", cancellationToken);
        if (res.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }

        res.EnsureSuccessStatusCode();
        return await res.Content.ReadFromJsonAsync<GetMovieResponse>(cancellationToken);
    }

    public async Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req, CancellationToken cancellationToken = default)
    {
        var res = await _http.PostAsJsonAsync("api/movies", req, cancellationToken);
        res.EnsureSuccessStatusCode();
        return (await res.Content.ReadFromJsonAsync<CreateMovieResponse>(cancellationToken))!;
    }

    public async Task<bool> UpdateAsync(UpdateMovieRequest req, CancellationToken cancellationToken = default)
    {
        var res = await _http.PutAsJsonAsync($"api/movies/{req.Id}", req, cancellationToken);
        if (res.StatusCode == HttpStatusCode.NoContent) return true;
        if (res.StatusCode == HttpStatusCode.NotFound) return false;
        res.EnsureSuccessStatusCode();
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteMovieRequest req, CancellationToken cancellationToken = default)
    {
        var res = await _http.DeleteAsync($"api/movies/{req.Id}", cancellationToken);
        if (res.StatusCode == HttpStatusCode.NoContent) return true;
        if (res.StatusCode == HttpStatusCode.NotFound) return false;
        res.EnsureSuccessStatusCode();
        return true;
    }
}
