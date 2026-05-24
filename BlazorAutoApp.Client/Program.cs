using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using BlazorAutoApp.Client.Features.Movies;
using BlazorAutoApp.Core.Features.Movies.Contracts;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

builder.Services.AddAuthorizationCore();
builder.Services.AddCascadingAuthenticationState();
builder.Services.AddAuthenticationStateDeserialization();

builder.Services.AddScoped(sp => new HttpClient
{
    BaseAddress = new Uri(builder.HostEnvironment.BaseAddress)
});

// Movies service for WASM after hydration
builder.Services.AddScoped<IMoviesApi, MoviesClientService>();

await builder.Build().RunAsync();

