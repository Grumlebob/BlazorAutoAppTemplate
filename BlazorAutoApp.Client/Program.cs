using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Client.Services;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

builder.Services.AddScoped(sp => new HttpClient
{
    BaseAddress = new Uri(builder.HostEnvironment.BaseAddress)
});

// Movies service for WASM after hydration
builder.Services.AddScoped<IMoviesApi, MoviesClientService>();

await builder.Build().RunAsync();
