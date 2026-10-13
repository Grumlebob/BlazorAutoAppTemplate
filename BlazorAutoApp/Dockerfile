# syntax=docker/dockerfile:1.24

FROM node:26.11.1-bookworm-slim AS react-dependencies
WORKDIR /src/BlazorAutoApp.React
COPY BlazorAutoApp.React/package.json BlazorAutoApp.React/package-lock.json BlazorAutoApp.React/.npmrc ./
RUN npm install --global npm@12.2.0 && npm ci

FROM react-dependencies AS react-assets
COPY BlazorAutoApp.React/ ./
RUN npm run build && test -s build/client/index.html

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS base
WORKDIR /app
RUN mkdir -p /app/Storage && chown -R app:app /app/Storage
EXPOSE 8080
EXPOSE 7186

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS source
WORKDIR /src
COPY global.json ./
COPY Directory.Build.props ./
COPY Directory.Build.targets ./
COPY Directory.Packages.props ./
COPY frontend-profile.txt ./
COPY BlazorAutoApp/BlazorAutoApp.csproj BlazorAutoApp/
COPY BlazorAutoApp.Client/BlazorAutoApp.Client.csproj BlazorAutoApp.Client/
COPY BlazorAutoApp.Core/BlazorAutoApp.Core.csproj BlazorAutoApp.Core/
COPY BlazorAutoApp/ BlazorAutoApp/
COPY BlazorAutoApp.Client/ BlazorAutoApp.Client/
COPY BlazorAutoApp.Core/ BlazorAutoApp.Core/

FROM source AS publish-blazor
ARG FRONTEND_PROFILE_OVERRIDE
RUN set -eu; \
    profile="${FRONTEND_PROFILE_OVERRIDE:-$(cat frontend-profile.txt)}"; \
    test "$profile" = "BlazorAuto" || { echo "final-blazor requires FRONTEND_PROFILE_OVERRIDE=BlazorAuto (received '$profile')" >&2; exit 2; }; \
    dotnet publish ./BlazorAutoApp/BlazorAutoApp.csproj -c Release -o /app/publish /p:UseAppHost=false "-p:FrontendProfile=$profile"

FROM source AS publish-react
ARG FRONTEND_PROFILE_OVERRIDE
COPY --from=react-assets /src/BlazorAutoApp.React/build/client/ /tmp/react-client/
RUN set -eu; \
    profile="${FRONTEND_PROFILE_OVERRIDE:-$(cat frontend-profile.txt)}"; \
    test "$profile" = "React" || { echo "final-react requires FRONTEND_PROFILE_OVERRIDE=React (received '$profile')" >&2; exit 2; }; \
    test -s /tmp/react-client/index.html || { echo "React static build is missing index.html" >&2; exit 2; }; \
    rm -rf ./BlazorAutoApp/Frontend/React/wwwroot; \
    mkdir -p ./BlazorAutoApp/Frontend/React/wwwroot; \
    cp -a /tmp/react-client/. ./BlazorAutoApp/Frontend/React/wwwroot/; \
    dotnet publish ./BlazorAutoApp/BlazorAutoApp.csproj -c Release -o /app/publish /p:UseAppHost=false "-p:FrontendProfile=$profile"

FROM base AS final-blazor
LABEL com.blazorautoapp.frontend-profile="BlazorAuto" \
      com.blazorautoapp.acceptance-profile="BlazorAutoV1"
WORKDIR /app
COPY --from=publish-blazor --chown=app:app /app/publish .
USER app
ENTRYPOINT ["dotnet", "BlazorAutoApp.dll"]

FROM base AS final-react
LABEL com.blazorautoapp.frontend-profile="React" \
      com.blazorautoapp.acceptance-profile="ReactPublicV1"
WORKDIR /app
COPY --from=publish-react --chown=app:app /app/publish .
USER app
ENTRYPOINT ["dotnet", "BlazorAutoApp.dll"]
