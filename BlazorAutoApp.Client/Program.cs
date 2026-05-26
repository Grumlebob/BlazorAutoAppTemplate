using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using BlazorAutoApp.Client.Features.Books;
using BlazorAutoApp.Client.Features.Books.UserBookcase;
using BlazorAutoApp.Core.Features.Books.Contracts;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

builder.Services.AddAuthorizationCore();
builder.Services.AddCascadingAuthenticationState();
builder.Services.AddAuthenticationStateDeserialization();

builder.Services.AddScoped(sp => new HttpClient
{
    BaseAddress = new Uri(builder.HostEnvironment.BaseAddress)
});

// Books service for WASM after hydration
builder.Services.AddScoped<IBooksApi, BooksClientService>();
builder.Services.AddScoped<UserBookcaseState>();

await builder.Build().RunAsync();
