# syntax=docker/dockerfile:1.7-labs

FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8080
EXPOSE 8443

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy project files first for better layer caching
COPY BlazorAutoApp/BlazorAutoApp.csproj BlazorAutoApp/
COPY BlazorAutoApp.Client/BlazorAutoApp.Client.csproj BlazorAutoApp.Client/
COPY BlazorAutoApp.Core/BlazorAutoApp.Core.csproj BlazorAutoApp.Core/

# Restore only the web app graph to avoid pulling test projects
RUN dotnet restore ./BlazorAutoApp/BlazorAutoApp.csproj

# Copy the full sources
COPY BlazorAutoApp/ BlazorAutoApp/
COPY BlazorAutoApp.Client/ BlazorAutoApp.Client/
COPY BlazorAutoApp.Core/ BlazorAutoApp.Core/

RUN dotnet build ./BlazorAutoApp/BlazorAutoApp.csproj -c Release -o /app/build --no-restore

FROM build AS publish
RUN dotnet publish ./BlazorAutoApp/BlazorAutoApp.csproj -c Release -o /app/publish /p:UseAppHost=false --no-restore

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .

# Kestrel endpoints and certificate are configured via appsettings.Docker.json
ENTRYPOINT ["dotnet", "BlazorAutoApp.dll"]
