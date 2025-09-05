namespace BlazorAutoApp.Features.Movies;

public class MoviesCacheOptions
{
    public int ListTtlMinutes { get; set; } = 5;
    public int ItemTtlMinutes { get; set; } = 10;
}

