using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.DeleteMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;

namespace BlazorAutoApp.Core.Features.Movies.Contracts;

public interface IMoviesApi
{
    Task<GetMoviesResponse> GetAsync(GetMoviesRequest req);
    Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req);
    Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req);
    Task<bool> UpdateAsync(UpdateMovieRequest req);
    Task<bool> DeleteAsync(DeleteMovieRequest req);
}
