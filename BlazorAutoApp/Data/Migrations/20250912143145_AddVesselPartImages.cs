using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddVesselPartImages : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "HullImageId",
                table: "InspectionVesselParts");

            migrationBuilder.AddColumn<int>(
                name: "InspectionVesselPartId",
                table: "HullImages",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_HullImages_InspectionVesselPartId",
                table: "HullImages",
                column: "InspectionVesselPartId");

            migrationBuilder.AddForeignKey(
                name: "FK_HullImages_InspectionVesselParts_InspectionVesselPartId",
                table: "HullImages",
                column: "InspectionVesselPartId",
                principalTable: "InspectionVesselParts",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_HullImages_InspectionVesselParts_InspectionVesselPartId",
                table: "HullImages");

            migrationBuilder.DropIndex(
                name: "IX_HullImages_InspectionVesselPartId",
                table: "HullImages");

            migrationBuilder.DropColumn(
                name: "InspectionVesselPartId",
                table: "HullImages");

            migrationBuilder.AddColumn<int>(
                name: "HullImageId",
                table: "InspectionVesselParts",
                type: "integer",
                nullable: true);
        }
    }
}
