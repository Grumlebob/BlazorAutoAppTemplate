using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class RemoveInspectionsFeature : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "CoatingConditions");

            migrationBuilder.DropTable(
                name: "FoulingObservations");

            migrationBuilder.DropTable(
                name: "HullConditions");

            migrationBuilder.DropTable(
                name: "HullImages");

            migrationBuilder.DropTable(
                name: "HullRatings");

            migrationBuilder.DropTable(
                name: "Inspections");

            migrationBuilder.DropTable(
                name: "InspectionVesselParts");

            migrationBuilder.DropTable(
                name: "VesselPartDetails");

            migrationBuilder.DropTable(
                name: "InspectionFlows");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "InspectionFlows",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    InspectionType = table.Column<int>(type: "integer", nullable: false),
                    VesselName = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_InspectionFlows", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Inspections",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    CreatedAtUtc = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Inspections", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "VesselPartDetails",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    InspectionVesselPartId = table.Column<int>(type: "integer", nullable: false),
                    Notes = table.Column<string>(type: "character varying(4000)", maxLength: 4000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_VesselPartDetails", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "InspectionVesselParts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    InspectionId = table.Column<Guid>(type: "uuid", nullable: false),
                    PartCode = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false)
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

            migrationBuilder.CreateTable(
                name: "CoatingConditions",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Blisters = table.Column<bool>(type: "boolean", nullable: false),
                    IntactPercent = table.Column<int>(type: "integer", nullable: false),
                    Peeling = table.Column<bool>(type: "boolean", nullable: false),
                    Scratching = table.Column<bool>(type: "boolean", nullable: false),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false)
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
                    CoveragePercent = table.Column<int>(type: "integer", nullable: true),
                    FoulingType = table.Column<int>(type: "integer", nullable: false),
                    IsPresent = table.Column<bool>(type: "boolean", nullable: false),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false)
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
                    Corrosion = table.Column<bool>(type: "boolean", nullable: false),
                    Cracks = table.Column<bool>(type: "boolean", nullable: false),
                    Dents = table.Column<bool>(type: "boolean", nullable: false),
                    IntegrityPercent = table.Column<int>(type: "integer", nullable: false),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false)
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
                    Rating = table.Column<int>(type: "integer", nullable: false),
                    Rationale = table.Column<string>(type: "text", nullable: true),
                    VesselPartDetailsId = table.Column<int>(type: "integer", nullable: false)
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

            migrationBuilder.CreateTable(
                name: "HullImages",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    AiHullScore = table.Column<double>(type: "double precision", nullable: false, defaultValue: 0.0),
                    ByteSize = table.Column<long>(type: "bigint", nullable: false),
                    ContentType = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    CreatedAtUtc = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    Height = table.Column<int>(type: "integer", nullable: true),
                    InspectionVesselPartId = table.Column<int>(type: "integer", nullable: true),
                    Notes = table.Column<string>(type: "text", nullable: true),
                    OriginalFileName = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    Sha256 = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: true),
                    Status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    StorageKey = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    VesselName = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false, defaultValue: "BoatyBoat"),
                    Width = table.Column<int>(type: "integer", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_HullImages", x => x.Id);
                    table.ForeignKey(
                        name: "FK_HullImages_InspectionVesselParts_InspectionVesselPartId",
                        column: x => x.InspectionVesselPartId,
                        principalTable: "InspectionVesselParts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
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
                name: "IX_HullImages_InspectionVesselPartId",
                table: "HullImages",
                column: "InspectionVesselPartId");

            migrationBuilder.CreateIndex(
                name: "IX_HullRatings_VesselPartDetailsId",
                table: "HullRatings",
                column: "VesselPartDetailsId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_InspectionVesselParts_InspectionId_PartCode",
                table: "InspectionVesselParts",
                columns: new[] { "InspectionId", "PartCode" });

            migrationBuilder.CreateIndex(
                name: "IX_VesselPartDetails_InspectionVesselPartId",
                table: "VesselPartDetails",
                column: "InspectionVesselPartId",
                unique: true);
        }
    }
}
