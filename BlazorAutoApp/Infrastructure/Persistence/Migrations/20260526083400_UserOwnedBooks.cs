using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BlazorAutoApp.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class UserOwnedBooks : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DELETE FROM \"Books\";");

            migrationBuilder.AddColumn<string>(
                name: "OwnerUserId",
                table: "Books",
                type: "character varying(450)",
                maxLength: 450,
                nullable: false,
                defaultValue: "");

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

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Books_AspNetUsers_OwnerUserId",
                table: "Books");

            migrationBuilder.DropIndex(
                name: "IX_Books_OwnerUserId",
                table: "Books");

            migrationBuilder.DropColumn(
                name: "OwnerUserId",
                table: "Books");
        }
    }
}
