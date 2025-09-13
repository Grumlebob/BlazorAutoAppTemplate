using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class VesselPartDetails : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "VesselPartDetails",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    InspectionVesselPartId = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_VesselPartDetails", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "CoatingConditions",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false),
                    IntactPercent = table.Column<int>(type: "integer", nullable: false),
                    Peeling = table.Column<bool>(type: "boolean", nullable: false),
                    Blisters = table.Column<bool>(type: "boolean", nullable: false),
                    Scratching = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CoatingConditions", x => x.Id);
                    table.ForeignKey(
                        name: "FK_CoatingConditions_VesselPartDetails_VesselPartDetailsId",
                        column: x => x.VesselPartDetailsId,
                        principalTable: "VesselPartDetails",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "FoulingObservations",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false),
                    FoulingType = table.Column<int>(type: "integer", nullable: false),
                    IsPresent = table.Column<bool>(type: "boolean", nullable: false),
                    CoveragePercent = table.Column<int>(type: "integer", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_FoulingObservations", x => x.Id);
                    table.ForeignKey(
                        name: "FK_FoulingObservations_VesselPartDetails_VesselPartDetailsId",
                        column: x => x.VesselPartDetailsId,
                        principalTable: "VesselPartDetails",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "HullConditions",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false),
                    IntegrityPercent = table.Column<int>(type: "integer", nullable: false),
                    Corrosion = table.Column<bool>(type: "boolean", nullable: false),
                    Dents = table.Column<bool>(type: "boolean", nullable: false),
                    Cracks = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_HullConditions", x => x.Id);
                    table.ForeignKey(
                        name: "FK_HullConditions_VesselPartDetails_VesselPartDetailsId",
                        column: x => x.VesselPartDetailsId,
                        principalTable: "VesselPartDetails",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "HullRatings",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false),
                    Rating = table.Column<int>(type: "integer", nullable: false),
                    Rationale = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_HullRatings", x => x.Id);
                    table.ForeignKey(
                        name: "FK_HullRatings_VesselPartDetails_VesselPartDetailsId",
                        column: x => x.VesselPartDetailsId,
                        principalTable: "VesselPartDetails",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_CoatingConditions_VesselPartDetailsId",
                table: "CoatingConditions",
                column: "VesselPartDetailsId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_FoulingObservations_VesselPartDetailsId",
                table: "FoulingObservations",
                column: "VesselPartDetailsId");

            migrationBuilder.CreateIndex(
                name: "IX_HullConditions_VesselPartDetailsId",
                table: "HullConditions",
                column: "VesselPartDetailsId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_HullRatings_VesselPartDetailsId",
                table: "HullRatings",
                column: "VesselPartDetailsId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_VesselPartDetails_InspectionVesselPartId",
                table: "VesselPartDetails",
                column: "InspectionVesselPartId",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "CoatingConditions");

            migrationBuilder.DropTable(
                name: "FoulingObservations");

            migrationBuilder.DropTable(
                name: "HullConditions");

            migrationBuilder.DropTable(
                name: "HullRatings");

            migrationBuilder.DropTable(
                name: "VesselPartDetails");
        }
    }
}
