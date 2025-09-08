namespace BlazorAutoApp.Core.Features.Movies;

public interface IMoviesApi
{
    Task<GetMoviesResponse> GetAsync(GetMoviesRequest req);
    Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req);
    Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req);
    Task<bool> UpdateAsync(UpdateMovieRequest req);
    Task<bool> DeleteAsync(DeleteMovieRequest req);
}
