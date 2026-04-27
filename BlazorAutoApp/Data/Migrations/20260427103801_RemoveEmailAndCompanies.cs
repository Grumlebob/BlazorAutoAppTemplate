using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class RemoveEmailAndCompanies : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Inspections_CompanyDetails_CompanyId",
                table: "Inspections");

            migrationBuilder.DropTable(
                name: "CompanyDetails");

            migrationBuilder.DropIndex(
                name: "IX_Inspections_CompanyId",
                table: "Inspections");

            migrationBuilder.DropColumn(
                name: "CompanyId",
                table: "Inspections");

            migrationBuilder.DropColumn(
                name: "CompanyId",
                table: "InspectionFlows");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "CompanyId",
                table: "Inspections",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.AddColumn<int>(
                name: "CompanyId",
                table: "InspectionFlows",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.CreateTable(
                name: "CompanyDetails",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Email = table.Column<string>(type: "character varying(320)", maxLength: 320, nullable: false),
                    HasActivatedLatestInspectionEmail = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    Name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CompanyDetails", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Inspections_CompanyId",
                table: "Inspections",
                column: "CompanyId");

            migrationBuilder.AddForeignKey(
                name: "FK_Inspections_CompanyDetails_CompanyId",
                table: "Inspections",
                column: "CompanyId",
                principalTable: "CompanyDetails",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
