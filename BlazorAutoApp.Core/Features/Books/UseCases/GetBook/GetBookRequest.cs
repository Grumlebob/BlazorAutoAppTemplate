namespace BlazorAutoApp.Core.Features.Books.UseCases.GetBook;

public class GetBookRequest
{
    public int Id { get; set; }

    public bool? ForceRefresh { get; set; }
}
