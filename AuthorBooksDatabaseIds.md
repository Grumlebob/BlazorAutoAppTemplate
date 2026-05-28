# Author Books Database IDs

## Goal

Status: Completed

Remove the stale author book `Slug` concept and move author/template books into the database using PostgreSQL-generated integer IDs.

Accepted model:

```text
Books
- Id int identity primary key
- Title
- Author
- Url

UserBooks
- BookId int primary key / FK Books.Id
- OwnerUserId FK AspNetUsers.Id

AuthorBooks
- BookId int primary key / FK Books.Id
- SeedKey unique
```

The important distinction:

- `Books` stores the shared book fields once.
- `UserBooks` says "this book belongs to this user and is editable by that user."
- `AuthorBooks` says "this book is part of the public author/template shelf and is view-only."

No `SortOrder`: ordering is not important for this template.

Keep `SeedKey`: it is the internal seed/upsert identity. It is not a route, not a slug, and not user-facing.

## Current State

Status: Completed

Findings:

- `AuthorBookPage.Slug` exists only to support the old `/books/author/{Slug}` redirect route.
- The current UI already links author books with numeric query IDs:

  ```text
  /books?authorBookId={id}&bookMode=view
  ```

- `BookModalHost` currently reads author books from the static client catalog.
- The existing `Books` table currently mixes core book fields with `OwnerUserId`.
- User book APIs are correctly authenticated and cache by user ID.

Conclusion:

- `Slug` is stale and should be removed.
- The database should be normalized before adding database-backed author books.
- Public author books should not be merged into user ownership rules.

## Why Keep SeedKey

Status: Accepted

PostgreSQL generates `Books.Id`. The app should not assume seed rows always get the same integer ID across fresh databases.

`SeedKey` allows safe repeatable seeding:

```text
SeedKey = "ship"
Title = "Ship"
```

Seed behavior:

- If `SeedKey = "ship"` exists, update the referenced `Books` row.
- If it does not exist, insert a new `Books` row, then insert an `AuthorBooks` row pointing at it.

`SeedKey` is internal only. UI navigation still uses `BookId`.

## Non-Goals

Status: Reviewed

- Do not add slugs again.
- Do not preserve `/books/author/{Slug}` unless explicitly requested later.
- Do not hardcode database IDs.
- Do not add author book editing UI.
- Do not make author books editable through user book APIs.
- Do not add images/uploads.
- Do not change deployment or Cloudflare behavior.
- Do not use this schema change as a Lighthouse optimization.

## Data Model

Status: Completed

Update `Book`:

```csharp
public class Book
{
    public int Id { get; set; }
    public required string Title { get; set; }
    public string? Author { get; set; }
    public string? Url { get; set; }
}
```

Add `UserBook`:

```csharp
public class UserBook
{
    public int BookId { get; set; }
    public required string OwnerUserId { get; set; }
    public Book Book { get; set; } = null!;
}
```

Add `AuthorBook`:

```csharp
public class AuthorBook
{
    public int BookId { get; set; }
    public required string SeedKey { get; set; }
    public Book Book { get; set; } = null!;
}
```

Configuration:

- `Books.Id` remains generated on add.
- `UserBooks.BookId` is primary key and FK to `Books.Id`.
- `UserBooks.OwnerUserId` is required and FK to `AspNetUsers.Id`.
- `AuthorBooks.BookId` is primary key and FK to `Books.Id`.
- `AuthorBooks.SeedKey` is required and unique.
- Deletes cascade from `Books` to subtype rows.
- User deletion cascades from `AspNetUsers` to `UserBooks`; corresponding `Books` cleanup should be considered explicitly if needed later.

## Migration Strategy

Status: Completed

Added migration `20260528104203_NormalizeBooksForAuthorBooks`, preserving existing user books:

1. Drop the old `Books.OwnerUserId` FK/index while keeping the column available for copying.
2. Create `AuthorBooks`.
3. Create `UserBooks`.
4. Copy existing ownership data:

   ```sql
   INSERT INTO "UserBooks" ("BookId", "OwnerUserId")
   SELECT "Id", "OwnerUserId"
   FROM "Books"
   WHERE "OwnerUserId" IS NOT NULL AND "OwnerUserId" <> '';
   ```

5. Drop the old `Books.OwnerUserId` column.
6. Add downgrade logic that restores `OwnerUserId` from `UserBooks` and removes author-only books.

No seed data is inserted in the migration because `Books.Id` is generated naturally.

Original requirements:

1. Create `UserBooks`.
2. Copy existing ownership data:

   ```sql
   INSERT INTO "UserBooks" ("BookId", "OwnerUserId")
   SELECT "Id", "OwnerUserId" FROM "Books";
   ```

3. Add FK/indexes for `UserBooks`.
4. Drop the old `Books.OwnerUserId` column.
5. Create `AuthorBooks`.
6. Add unique index on `AuthorBooks.SeedKey`.

## Seeding

Status: Completed

Seed these author books using `SeedKey`:

```text
the-great-gatsby | The Great Gatsby | F. Scott Fitzgerald | https://www.gutenberg.org/ebooks/64317
ship             | Ship             | Jacob Grum          | null
traceback        | TraceBack        | Jacob Grum          | null
improveddb       | ImprovedDb       | Jacob Grum          | null
kinojoin         | KinoJoin         | Jacob Grum          | null
```

Requirements:

- Seed after migrations.
- Use `SeedKey` for idempotence.
- Do not assume generated IDs.
- Prefer transactionally safe upsert logic.
- Keep it safe if multiple app nodes run seed at the same time.
- Do not delete extra author books automatically.

Simple acceptable approach:

- Query existing `AuthorBooks` by seed keys.
- Update existing linked `Books` rows.
- Insert missing `Books` rows and matching `AuthorBooks` rows.
- Enforce unique `SeedKey` so duplicate rows cannot be created.

If concurrency is a concern in production startup, use PostgreSQL `ON CONFLICT` or an advisory lock around the seed.

Implemented with a PostgreSQL transaction-level advisory lock and idempotent update/insert by `SeedKey`.

## Public Author Book API

Status: Completed

Add public read-only author book endpoints:

```text
GET /api/author-books
GET /api/author-books/{id:int}
```

Rules:

- No authorization required.
- No create/update/delete endpoints.
- Use `TypedResults`.
- Use `ProblemDetails` for 404.
- Use `AsNoTracking`.
- Cache list and item reads separately from user books.
- Return book IDs from `Books.Id`.

DTOs:

```csharp
AuthorBookListItemResponse
AuthorBookResponse
GetAuthorBooksResponse
GetAuthorBookRequest
```

## Client Changes

Status: Completed

Replace the static author catalog with a data-backed state/service:

- Add `IAuthorBooksApi` in Core.
- Add server implementation using `AppDbContext`.
- Add WASM/client implementation using HTTP.
- Add `AuthorBookcaseState` in the client slice.
- `AuthorBookcase` loads from `AuthorBookcaseState`.
- Convert API responses to `BookcaseBook`.
- Links remain:

  ```text
  /books?authorBookId={id}&bookMode=view
  ```

- `BookModalHost` loads author book details through `IAuthorBooksApi.GetByIdAsync`.
- Author books remain view-only.
- User books remain editable.

## Routing Cleanup

Status: Completed

Remove:

- `AuthorBookPage`
- `AuthorBookcaseCatalog`
- `AuthorBookDetails.razor`
- `/books/author/{Slug}`

Do not replace it with another slug route.

Optional later:

- If a direct URL is needed, add `/books/author/{id:int}` only.

## Caching

Status: Completed

Add author-specific cache keys:

```text
AuthorBooks:List
AuthorBooks:Item:{id}
AuthorBooks:All
```

Do not reuse user `BooksCacheKeys`.

Expected behavior:

- First public read can hit Postgres.
- Warm reads should come from `HybridCache`.
- Seed should invalidate author book cache after inserts/updates.

## Tests

Status: Completed

Add/update:

- Migration/model tests cover `Books`, `UserBooks`, and `AuthorBooks`.
- Existing user book CRUD tests still pass.
- User book service queries through `UserBooks`.
- Author book seed inserts missing rows.
- Author book seed updates existing rows by `SeedKey`.
- Author book seed is idempotent.
- Author book seed does not assume fixed IDs.
- `GET /api/author-books` returns seeded author books.
- `GET /api/author-books/{id}` returns one author book.
- Missing author book returns 404 ProblemDetails.
- Author bookcase links use `authorBookId={id}`.
- Existing visible E2E still passes for author and user book flows.

Implemented focused coverage for:

- User book CRUD through `UserBooks`.
- Public author book list/detail endpoints.
- 404 ProblemDetails for missing author books.
- Startup author seeding idempotence and update-by-`SeedKey`.
- Endpoint surface and DI wiring.
- Visible E2E author/user book flows.

## Performance Review

Status: Completed

This is not expected to improve Lighthouse directly. It should not meaningfully hurt it either if cached.

Why:

- Five author rows are tiny.
- Home's current Lighthouse bottleneck is Interactive Auto / WebAssembly startup, not the static author catalog.
- A warm cached DB-backed author list should be negligible.

Check after implementation:

```powershell
.\RunLighthouse.ps1 `
  -BaseUrl https://127.0.0.1:7186 `
  -Paths "/" `
  -Profile mobile `
  -Label local-author-books-db-after `
  -IgnoreCertificateErrors
```

Result on 2026-05-28:

```text
performance=63, accessibility=100, best-practices=100, seo=100
Report: TestResults/Lighthouse/local-author-books-db-after-20260528-125118
```

## Validation Gate

Status: Completed

Run:

```powershell
npm --prefix .\BlazorAutoApp.Client run css:build
dotnet build .\BlazorAutoApp.sln -c Release --no-restore
dotnet test .\BlazorAutoApp.sln -c Release --no-build
dotnet format .\BlazorAutoApp.sln --verify-no-changes --no-restore
git diff --check
.\RunLocal.ps1 -NoBrowser
```

Executed:

- `npm --prefix .\BlazorAutoApp.Client run css:build`
- `git diff --exit-code -- BlazorAutoApp\wwwroot\tailwind.css BlazorAutoApp.Client\package-lock.json`
- `dotnet build .\BlazorAutoApp.sln --configuration Release --no-restore`
- `dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --configuration Release --no-build`
- `dotnet format .\BlazorAutoApp.sln --verify-no-changes --verbosity minimal`
- `git diff --check`
- `.\RunLocal.ps1 -NoBrowser -TimeoutSeconds 240`
- Visible E2E: `RUN_E2E=1`, `E2E_BASE_URL=https://127.0.0.1:7186`, `E2E_HEADLESS=0`, `FullyQualifiedName~E2E`
- Lighthouse mobile for `/`

Results:

- Release build: passed with 0 warnings.
- Tests: passed, 80 passed / 5 skipped E2E in the normal test run.
- Visible E2E: passed, 5 passed / 0 skipped.
- Local Docker app: ready at `https://localhost:7186`.

Because routing/modal behavior changes, also run visible E2E:

```powershell
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://127.0.0.1:7186'
$env:E2E_HEADLESS='0'
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj -c Release --no-build --filter FullyQualifiedName~E2E
```

## Done Criteria

Status: Completed

- `Slug` is removed.
- Static author catalog is removed.
- `Books` contains shared book fields only.
- `UserBooks` contains ownership.
- `AuthorBooks` contains `SeedKey`.
- IDs are generated by PostgreSQL.
- Author books are seeded idempotently.
- Author book UI and modal load by ID.
- User book CRUD remains correct.
- Tests, visible E2E, and validation pass.
