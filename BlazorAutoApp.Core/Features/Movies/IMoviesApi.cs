using System.Threading.Tasks;

namespace BlazorAutoApp.Core.Features.Movies;

public interface IMoviesApi
{
    Task<GetMoviesResponse> GetAsync(GetMoviesRequest req);
    Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req);
    Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req);
    Task<UpdateMovieResponse?> UpdateAsync(UpdateMovieRequest req);
    Task<DeleteMovieResponse?> DeleteAsync(DeleteMovieRequest req);
}

