using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BlazorAutoApp.Data.Migrations
{
    /// <inheritdoc />
    public partial class PasswordRemoval : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "PasswordHash",
                table: "Inspections");

            migrationBuilder.DropColumn(
                name: "PasswordSalt",
                table: "Inspections");

            migrationBuilder.DropColumn(
                name: "VerifiedAtUtc",
                table: "Inspections");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "PasswordHash",
                table: "Inspections",
                type: "character varying(512)",
                maxLength: 512,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "PasswordSalt",
                table: "Inspections",
                type: "character varying(512)",
                maxLength: 512,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<DateTime>(
                name: "VerifiedAtUtc",
                table: "Inspections",
                type: "timestamp with time zone",
                nullable: true);
        }
    }
}
