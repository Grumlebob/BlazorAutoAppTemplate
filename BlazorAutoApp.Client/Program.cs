using BlazorAutoApp.Client.Features.IdentityShowcase;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using BlazorAutoApp.Client.Features.Movies;
using BlazorAutoApp.Core.Features.IdentityShowcase.Contracts;
using BlazorAutoApp.Core.Features.Movies.Contracts;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

builder.Services.AddScoped(sp => new HttpClient
{
    BaseAddress = new Uri(builder.HostEnvironment.BaseAddress)
});

// Movies service for WASM after hydration
builder.Services.AddScoped<IMoviesApi, MoviesClientService>();
builder.Services.AddScoped<IIdentityShowcaseApi, IdentityShowcaseClientService>();

await builder.Build().RunAsync();

