using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Movies;

namespace BlazorAutoApp.Client.Services;

public class MoviesClientService : IMoviesApi
{
    private readonly HttpClient _http;

    public MoviesClientService(HttpClient http)
    {
        _http = http;
    }

    public async Task<GetMoviesResponse> GetAsync(GetMoviesRequest req)
    {
        var res = await _http.GetFromJsonAsync<GetMoviesResponse>("api/movies");
        return res ?? new GetMoviesResponse { Movies = new List<Movie>() };
    }

    public async Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req)
    {
        return await _http.GetFromJsonAsync<GetMovieResponse>($"api/movies/{req.Id}");
    }

    public async Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req)
    {
        var res = await _http.PostAsJsonAsync("api/movies", req);
        res.EnsureSuccessStatusCode();
        return (await res.Content.ReadFromJsonAsync<CreateMovieResponse>())!;
    }

    public async Task<UpdateMovieResponse?> UpdateAsync(UpdateMovieRequest req)
    {
        var res = await _http.PutAsJsonAsync($"api/movies/{req.Id}", req);
        if (!res.IsSuccessStatusCode) return null;
        return await res.Content.ReadFromJsonAsync<UpdateMovieResponse>();
    }

    public async Task<DeleteMovieResponse?> DeleteAsync(DeleteMovieRequest req)
    {
        var res = await _http.DeleteAsync($"api/movies/{req.Id}");
        if (!res.IsSuccessStatusCode) return null;
        return await res.Content.ReadFromJsonAsync<DeleteMovieResponse>();
    }
}

