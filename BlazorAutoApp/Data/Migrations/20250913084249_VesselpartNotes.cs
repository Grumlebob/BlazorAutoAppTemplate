using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class VesselpartNotes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Notes",
                table: "VesselPartDetails",
                type: "character varying(4000)",
                maxLength: 4000,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Notes",
                table: "VesselPartDetails");
        }
    }
}
