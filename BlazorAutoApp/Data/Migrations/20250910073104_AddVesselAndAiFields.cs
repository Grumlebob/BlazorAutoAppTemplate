using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddVesselAndAiFields : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Add columns if they don't exist (PostgreSQL)
            migrationBuilder.Sql("ALTER TABLE \"HullImages\" ADD COLUMN IF NOT EXISTS \"AiHullScore\" double precision;");
            migrationBuilder.Sql("ALTER TABLE \"HullImages\" ADD COLUMN IF NOT EXISTS \"VesselName\" character varying(128);");

            // Backfill values for existing rows
            migrationBuilder.Sql("UPDATE \"HullImages\" SET \"AiHullScore\" = COALESCE(\"AiHullScore\", 0.0);");
            migrationBuilder.Sql("UPDATE \"HullImages\" SET \"VesselName\" = COALESCE(NULLIF(\"VesselName\", ''), 'BoatyBoat');");

            // Enforce constraints and defaults going forward
            migrationBuilder.Sql("ALTER TABLE \"HullImages\" ALTER COLUMN \"VesselName\" SET NOT NULL;");
            migrationBuilder.Sql("ALTER TABLE \"HullImages\" ALTER COLUMN \"AiHullScore\" SET DEFAULT 0.0;");
            migrationBuilder.Sql("ALTER TABLE \"HullImages\" ALTER COLUMN \"VesselName\" SET DEFAULT 'BoatyBoat';");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("ALTER TABLE \"HullImages\" DROP COLUMN IF EXISTS \"AiHullScore\";");
            migrationBuilder.Sql("ALTER TABLE \"HullImages\" DROP COLUMN IF EXISTS \"VesselName\";");
        }
    }
}
