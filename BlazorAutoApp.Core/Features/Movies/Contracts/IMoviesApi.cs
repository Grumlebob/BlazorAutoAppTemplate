using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.DeleteMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;

namespace BlazorAutoApp.Core.Features.Movies.Contracts;

public interface IMoviesApi
{
    Task<GetMoviesResponse> GetAsync(GetMoviesRequest req, CancellationToken cancellationToken = default);
    Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req, CancellationToken cancellationToken = default);
    Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req, CancellationToken cancellationToken = default);
    Task<bool> UpdateAsync(UpdateMovieRequest req, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(DeleteMovieRequest req, CancellationToken cancellationToken = default);
}
