using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BlazorAutoApp.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class NormalizeBooksForAuthorBooks : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Books_AspNetUsers_OwnerUserId",
                table: "Books");

            migrationBuilder.DropIndex(
                name: "IX_Books_OwnerUserId",
                table: "Books");

            migrationBuilder.CreateTable(
                name: "AuthorBooks",
                columns: table => new
                {
                    BookId = table.Column<int>(type: "integer", nullable: false),
                    SeedKey = table.Column<string>(type: "character varying(96)", maxLength: 96, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AuthorBooks", x => x.BookId);
                    table.ForeignKey(
                        name: "FK_AuthorBooks_Books_BookId",
                        column: x => x.BookId,
                        principalTable: "Books",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "UserBooks",
                columns: table => new
                {
                    BookId = table.Column<int>(type: "integer", nullable: false),
                    OwnerUserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UserBooks", x => x.BookId);
                    table.ForeignKey(
                        name: "FK_UserBooks_AspNetUsers_OwnerUserId",
                        column: x => x.OwnerUserId,
                        principalTable: "AspNetUsers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_UserBooks_Books_BookId",
                        column: x => x.BookId,
                        principalTable: "Books",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_AuthorBooks_SeedKey",
                table: "AuthorBooks",
                column: "SeedKey",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_UserBooks_OwnerUserId",
                table: "UserBooks",
                column: "OwnerUserId");

            migrationBuilder.Sql(
                """
                INSERT INTO "UserBooks" ("BookId", "OwnerUserId")
                SELECT "Id", "OwnerUserId"
                FROM "Books"
                WHERE "OwnerUserId" IS NOT NULL AND "OwnerUserId" <> ''
                ON CONFLICT ("BookId") DO NOTHING;
                """);

            migrationBuilder.DropColumn(
                name: "OwnerUserId",
                table: "Books");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                DELETE FROM "Books"
                USING "AuthorBooks"
                WHERE "Books"."Id" = "AuthorBooks"."BookId";
                """);

            migrationBuilder.DropTable(
                name: "AuthorBooks");

            migrationBuilder.AddColumn<string>(
                name: "OwnerUserId",
                table: "Books",
                type: "character varying(450)",
                maxLength: 450,
                nullable: false,
                defaultValue: "");

            migrationBuilder.Sql(
                """
                UPDATE "Books"
                SET "OwnerUserId" = "UserBooks"."OwnerUserId"
                FROM "UserBooks"
                WHERE "Books"."Id" = "UserBooks"."BookId";
                """);

            migrationBuilder.Sql(
                """
                DELETE FROM "Books"
                WHERE "OwnerUserId" = '';
                """);

            migrationBuilder.DropTable(
                name: "UserBooks");

            migrationBuilder.CreateIndex(
                name: "IX_Books_OwnerUserId",
                table: "Books",
                column: "OwnerUserId");

            migrationBuilder.AddForeignKey(
                name: "FK_Books_AspNetUsers_OwnerUserId",
                table: "Books",
                column: "OwnerUserId",
                principalTable: "AspNetUsers",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
