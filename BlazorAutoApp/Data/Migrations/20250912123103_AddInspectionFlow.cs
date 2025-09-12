using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddInspectionFlow : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "InspectionFlows",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    CompanyId = table.Column<int>(type: "integer", nullable: false),
                    VesselName = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    InspectionType = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InspectionFlows", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "InspectionVesselParts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    InspectionId = table.Column<Guid>(type: "uuid", nullable: false),
                    PartCode = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    HullImageId = table.Column<int>(type: "integer", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InspectionVesselParts", x => x.Id);
                    table.ForeignKey(
                        name: "FK_InspectionVesselParts_InspectionFlows_InspectionId",
                        column: x => x.InspectionId,
                        principalTable: "InspectionFlows",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_InspectionVesselParts_InspectionId_PartCode",
                table: "InspectionVesselParts",
                columns: new[] { "InspectionId", "PartCode" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "InspectionVesselParts");

            migrationBuilder.DropTable(
                name: "InspectionFlows");
        }
    }
}
