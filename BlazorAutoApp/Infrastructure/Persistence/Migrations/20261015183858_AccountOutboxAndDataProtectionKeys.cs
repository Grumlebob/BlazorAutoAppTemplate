using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace BlazorAutoApp.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AccountOutboxAndDataProtectionKeys : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                DO $$
                DECLARE
                    duplicate_groups bigint;
                    incompatible_values bigint;
                BEGIN
                    SELECT COUNT(*) INTO duplicate_groups
                    FROM (
                        SELECT "NormalizedEmail"
                        FROM "AspNetUsers"
                        WHERE "NormalizedEmail" IS NOT NULL
                        GROUP BY "NormalizedEmail"
                        HAVING COUNT(*) > 1
                    ) duplicate_emails;

                    SELECT COUNT(*) INTO incompatible_values
                    FROM "AspNetUsers"
                    WHERE "NormalizedEmail" IS NOT NULL
                      AND length("NormalizedEmail") > 254;

                    IF duplicate_groups > 0 OR incompatible_values > 0 THEN
                        RAISE EXCEPTION
                            'Account schema migration refused: % duplicate normalized-email groups and % incompatible values. Back up the database and privately remediate these rows before retrying; this migration changed no account data.',
                            duplicate_groups,
                            incompatible_values
                            USING ERRCODE = '23514';
                    END IF;
                END $$;
                """);

            migrationBuilder.DropIndex(
                name: "EmailIndex",
                table: "AspNetUsers");

            migrationBuilder.CreateTable(
                name: "AccountOutbox",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    MessageId = table.Column<string>(type: "character varying(254)", maxLength: 254, nullable: false),
                    UserId = table.Column<string>(type: "character varying(450)", maxLength: 450, nullable: false),
                    Purpose = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    Status = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    ProtectedPayload = table.Column<string>(type: "text", nullable: false),
                    CreatedUtc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    ExpiresUtc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    NextAttemptUtc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    Attempts = table.Column<int>(type: "integer", nullable: false),
                    LeaseId = table.Column<string>(type: "character varying(36)", maxLength: 36, nullable: true),
                    LeaseUntilUtc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    FailureCode = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AccountOutbox", x => x.Id);
                    table.ForeignKey(
                        name: "FK_AccountOutbox_AspNetUsers_UserId",
                        column: x => x.UserId,
                        principalTable: "AspNetUsers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "DataProtectionKeys",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    FriendlyName = table.Column<string>(type: "text", nullable: true),
                    Xml = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DataProtectionKeys", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "EmailIndex",
                table: "AspNetUsers",
                column: "NormalizedEmail",
                unique: true,
                filter: "\"NormalizedEmail\" IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "IX_AccountOutbox_MessageId",
                table: "AccountOutbox",
                column: "MessageId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_AccountOutbox_Status_NextAttemptUtc",
                table: "AccountOutbox",
                columns: new[] { "Status", "NextAttemptUtc" });

            migrationBuilder.CreateIndex(
                name: "IX_AccountOutbox_UserId_Purpose",
                table: "AccountOutbox",
                columns: new[] { "UserId", "Purpose" },
                unique: true,
                filter: "\"Status\" IN ('Pending', 'Leased')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "AccountOutbox");

            migrationBuilder.DropTable(
                name: "DataProtectionKeys");

            migrationBuilder.DropIndex(
                name: "EmailIndex",
                table: "AspNetUsers");

            migrationBuilder.CreateIndex(
                name: "EmailIndex",
                table: "AspNetUsers",
                column: "NormalizedEmail");
        }
    }
}
