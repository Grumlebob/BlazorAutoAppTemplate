# syntax=docker/dockerfile:1.24

FROM node:26.12.1-bookworm-slim AS react-dependencies
WORKDIR /src/GrumPlates.React
COPY GrumPlates.React/package.json GrumPlates.React/package-lock.json GrumPlates.React/.npmrc ./
RUN npm install --global npm@12.2.0 && npm ci

FROM react-dependencies AS react-assets
COPY GrumPlates.React/ ./
# One app stylesheet: prerendered HTML must link the same CSS the client bundle loads,
# or hydration fails.
RUN npm run build && test -s build/client/index.html \
    && test "$(ls build/client/assets/app-*.css | wc -l)" -eq 1

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
COPY GrumPlates/GrumPlates.csproj GrumPlates/
COPY GrumPlates.Client/GrumPlates.Client.csproj GrumPlates.Client/
COPY GrumPlates.Core/GrumPlates.Core.csproj GrumPlates.Core/
COPY GrumPlates/ GrumPlates/
COPY GrumPlates.Client/ GrumPlates.Client/
COPY GrumPlates.Core/ GrumPlates.Core/

FROM source AS publish-blazor
ARG FRONTEND_PROFILE_OVERRIDE
RUN set -eu; \
    profile="${FRONTEND_PROFILE_OVERRIDE:-$(cat frontend-profile.txt)}"; \
    test "$profile" = "BlazorAuto" || { echo "final-blazor requires FRONTEND_PROFILE_OVERRIDE=BlazorAuto (received '$profile')" >&2; exit 2; }; \
    dotnet publish ./GrumPlates/GrumPlates.csproj -c Release -o /app/publish /p:UseAppHost=false "-p:FrontendProfile=$profile"

FROM source AS publish-react
ARG FRONTEND_PROFILE_OVERRIDE
COPY --from=react-assets /src/GrumPlates.React/build/client/ /tmp/react-client/
RUN set -eu; \
    profile="${FRONTEND_PROFILE_OVERRIDE:-$(cat frontend-profile.txt)}"; \
    test "$profile" = "React" || { echo "final-react requires FRONTEND_PROFILE_OVERRIDE=React (received '$profile')" >&2; exit 2; }; \
    test -s /tmp/react-client/index.html || { echo "React static build is missing index.html" >&2; exit 2; }; \
    rm -rf ./GrumPlates/Frontend/React/wwwroot; \
    mkdir -p ./GrumPlates/Frontend/React/wwwroot; \
    cp -a /tmp/react-client/. ./GrumPlates/Frontend/React/wwwroot/; \
    dotnet publish ./GrumPlates/GrumPlates.csproj -c Release -o /app/publish /p:UseAppHost=false "-p:FrontendProfile=$profile"

FROM base AS final-blazor
LABEL com.grumplates.frontend-profile="BlazorAuto" \
      com.grumplates.acceptance-profile="BlazorAutoV1"
WORKDIR /app
COPY --from=publish-blazor --chown=app:app /app/publish .
USER app
ENTRYPOINT ["dotnet", "GrumPlates.dll"]

FROM base AS final-react
LABEL com.grumplates.frontend-profile="React" \
      com.grumplates.acceptance-profile="ReactPublicV1"
WORKDIR /app
COPY --from=publish-react --chown=app:app /app/publish .
USER app
ENTRYPOINT ["dotnet", "GrumPlates.dll"]
