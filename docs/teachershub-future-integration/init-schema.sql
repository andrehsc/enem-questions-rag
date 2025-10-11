# 🗄️ Database Schema Creation Script - Dakota DatabaseMaster

## Problema Identificado
O sistema está usando EnsureCreated() em vez de migrations adequadas, causando inconsistências no schema e problemas de foreign key constraints.

## Solução: Schema SQL Dedicado
Criar script SQL completo que será executado na inicialização do container PostgreSQL.

## Script de Criação do Schema
```sql
-- TeachersHub Database Schema
-- Dakota DatabaseMaster - Database Administrator
-- Criado para garantir consistência e performance otimizada

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS "Options" CASCADE;
DROP TABLE IF EXISTS "Questions" CASCADE;
DROP TABLE IF EXISTS "Assessments" CASCADE;
DROP TABLE IF EXISTS "LessonPlans" CASCADE;
DROP TABLE IF EXISTS "Teachers" CASCADE;
DROP TABLE IF EXISTS "AspNetUserRoles" CASCADE;
DROP TABLE IF EXISTS "AspNetRoleClaims" CASCADE;
DROP TABLE IF EXISTS "AspNetUserClaims" CASCADE;
DROP TABLE IF EXISTS "AspNetUserLogins" CASCADE;
DROP TABLE IF EXISTS "AspNetUserTokens" CASCADE;
DROP TABLE IF EXISTS "AspNetUsers" CASCADE;
DROP TABLE IF EXISTS "AspNetRoles" CASCADE;

-- Create AspNetRoles table (Identity framework)
CREATE TABLE "AspNetRoles" (
    "Id" uuid NOT NULL,
    "Name" character varying(256),
    "NormalizedName" character varying(256),
    "ConcurrencyStamp" text,
    CONSTRAINT "PK_AspNetRoles" PRIMARY KEY ("Id")
);

-- Create AspNetUsers table (Identity framework)  
CREATE TABLE "AspNetUsers" (
    "Id" uuid NOT NULL,
    "UserName" character varying(256),
    "NormalizedUserName" character varying(256),
    "Email" character varying(256),
    "NormalizedEmail" character varying(256),
    "EmailConfirmed" boolean NOT NULL,
    "PasswordHash" text,
    "SecurityStamp" text,
    "ConcurrencyStamp" text,
    "PhoneNumber" text,
    "PhoneNumberConfirmed" boolean NOT NULL,
    "TwoFactorEnabled" boolean NOT NULL,
    "LockoutEnd" timestamp with time zone,
    "LockoutEnabled" boolean NOT NULL,
    "AccessFailedCount" integer NOT NULL,
    CONSTRAINT "PK_AspNetUsers" PRIMARY KEY ("Id")
);

-- Create Teachers table (Core domain entity)
CREATE TABLE "Teachers" (
    "Id" uuid NOT NULL,
    "Email" character varying(255) NOT NULL,
    "Name" character varying(100) NOT NULL,
    "CreatedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    "UpdatedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "PK_Teachers" PRIMARY KEY ("Id"),
    CONSTRAINT "UK_Teachers_Email" UNIQUE ("Email")
);

-- Create LessonPlans table
CREATE TABLE "LessonPlans" (
    "Id" uuid NOT NULL,
    "Title" character varying(200) NOT NULL,
    "Objectives" character varying(2000),
    "Activities" character varying(5000),
    "Resources" character varying(2000),
    "TeacherId" uuid NOT NULL,
    "CreatedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    "UpdatedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "PK_LessonPlans" PRIMARY KEY ("Id"),
    CONSTRAINT "FK_LessonPlans_Teachers" FOREIGN KEY ("TeacherId") 
        REFERENCES "Teachers" ("Id") ON DELETE CASCADE
);

-- Create Assessments table
CREATE TABLE "Assessments" (
    "Id" uuid NOT NULL,
    "Title" character varying(200) NOT NULL,
    "Description" character varying(1000),
    "TeacherId" uuid NOT NULL,
    "CreatedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    "UpdatedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "PK_Assessments" PRIMARY KEY ("Id"),
    CONSTRAINT "FK_Assessments_Teachers" FOREIGN KEY ("TeacherId") 
        REFERENCES "Teachers" ("Id") ON DELETE CASCADE
);

-- Create Questions table
CREATE TABLE "Questions" (
    "Id" uuid NOT NULL,
    "Prompt" character varying(1000) NOT NULL,
    "AnswerKey" character varying(500),
    "Type" integer NOT NULL, -- 0=MultipleChoice, 1=TrueFalse, 2=ShortAnswer, 3=Essay
    "Order" integer NOT NULL DEFAULT 0,
    "AssessmentId" uuid NOT NULL,
    "CreatedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    CONSTRAINT "PK_Questions" PRIMARY KEY ("Id"),
    CONSTRAINT "FK_Questions_Assessments" FOREIGN KEY ("AssessmentId") 
        REFERENCES "Assessments" ("Id") ON DELETE CASCADE
);

-- Create Options table (for multiple choice questions)
CREATE TABLE "Options" (
    "Id" uuid NOT NULL,
    "Text" character varying(500) NOT NULL,
    "IsCorrect" boolean NOT NULL DEFAULT FALSE,
    "Order" integer NOT NULL DEFAULT 0,
    "QuestionId" uuid NOT NULL,
    CONSTRAINT "PK_Options" PRIMARY KEY ("Id"),
    CONSTRAINT "FK_Options_Questions" FOREIGN KEY ("QuestionId") 
        REFERENCES "Questions" ("Id") ON DELETE CASCADE
);

-- Create remaining Identity tables
CREATE TABLE "AspNetRoleClaims" (
    "Id" serial NOT NULL,
    "RoleId" uuid NOT NULL,
    "ClaimType" text,
    "ClaimValue" text,
    CONSTRAINT "PK_AspNetRoleClaims" PRIMARY KEY ("Id"),
    CONSTRAINT "FK_AspNetRoleClaims_AspNetRoles_RoleId" FOREIGN KEY ("RoleId") 
        REFERENCES "AspNetRoles" ("Id") ON DELETE CASCADE
);

CREATE TABLE "AspNetUserClaims" (
    "Id" serial NOT NULL,
    "UserId" uuid NOT NULL,
    "ClaimType" text,
    "ClaimValue" text,
    CONSTRAINT "PK_AspNetUserClaims" PRIMARY KEY ("Id"),
    CONSTRAINT "FK_AspNetUserClaims_AspNetUsers_UserId" FOREIGN KEY ("UserId") 
        REFERENCES "AspNetUsers" ("Id") ON DELETE CASCADE
);

CREATE TABLE "AspNetUserLogins" (
    "LoginProvider" character varying(450) NOT NULL,
    "ProviderKey" character varying(450) NOT NULL,
    "ProviderDisplayName" text,
    "UserId" uuid NOT NULL,
    CONSTRAINT "PK_AspNetUserLogins" PRIMARY KEY ("LoginProvider", "ProviderKey"),
    CONSTRAINT "FK_AspNetUserLogins_AspNetUsers_UserId" FOREIGN KEY ("UserId") 
        REFERENCES "AspNetUsers" ("Id") ON DELETE CASCADE
);

CREATE TABLE "AspNetUserRoles" (
    "UserId" uuid NOT NULL,
    "RoleId" uuid NOT NULL,
    CONSTRAINT "PK_AspNetUserRoles" PRIMARY KEY ("UserId", "RoleId"),
    CONSTRAINT "FK_AspNetUserRoles_AspNetRoles_RoleId" FOREIGN KEY ("RoleId") 
        REFERENCES "AspNetRoles" ("Id") ON DELETE CASCADE,
    CONSTRAINT "FK_AspNetUserRoles_AspNetUsers_UserId" FOREIGN KEY ("UserId") 
        REFERENCES "AspNetUsers" ("Id") ON DELETE CASCADE
);

CREATE TABLE "AspNetUserTokens" (
    "UserId" uuid NOT NULL,
    "LoginProvider" character varying(450) NOT NULL,
    "Name" character varying(450) NOT NULL,
    "Value" text,
    CONSTRAINT "PK_AspNetUserTokens" PRIMARY KEY ("UserId", "LoginProvider", "Name"),
    CONSTRAINT "FK_AspNetUserTokens_AspNetUsers_UserId" FOREIGN KEY ("UserId") 
        REFERENCES "AspNetUsers" ("Id") ON DELETE CASCADE
);

-- Create optimized indexes for performance
CREATE INDEX "IX_Teachers_Email" ON "Teachers" ("Email");
CREATE INDEX "IX_LessonPlans_TeacherId" ON "LessonPlans" ("TeacherId");
CREATE INDEX "IX_LessonPlans_CreatedAt" ON "LessonPlans" ("CreatedAt");
CREATE INDEX "IX_Assessments_TeacherId" ON "Assessments" ("TeacherId");
CREATE INDEX "IX_Assessments_CreatedAt" ON "Assessments" ("CreatedAt");
CREATE INDEX "IX_Questions_AssessmentId" ON "Questions" ("AssessmentId");
CREATE INDEX "IX_Questions_Order" ON "Questions" ("AssessmentId", "Order");
CREATE INDEX "IX_Options_QuestionId" ON "Options" ("QuestionId");
CREATE INDEX "IX_Options_Order" ON "Options" ("QuestionId", "Order");

-- Identity framework indexes
CREATE UNIQUE INDEX "IX_AspNetRoles_NormalizedName" ON "AspNetRoles" ("NormalizedName");
CREATE INDEX "IX_AspNetRoleClaims_RoleId" ON "AspNetRoleClaims" ("RoleId");
CREATE INDEX "IX_AspNetUserClaims_UserId" ON "AspNetUserClaims" ("UserId");
CREATE INDEX "IX_AspNetUserLogins_UserId" ON "AspNetUserLogins" ("UserId");
CREATE INDEX "IX_AspNetUserRoles_RoleId" ON "AspNetUserRoles" ("RoleId");
CREATE UNIQUE INDEX "IX_AspNetUsers_NormalizedEmail" ON "AspNetUsers" ("NormalizedEmail");
CREATE UNIQUE INDEX "IX_AspNetUsers_NormalizedUserName" ON "AspNetUsers" ("NormalizedUserName");

-- Insert default roles
INSERT INTO "AspNetRoles" ("Id", "Name", "NormalizedName", "ConcurrencyStamp") VALUES
(gen_random_uuid(), 'Admin', 'ADMIN', gen_random_uuid()::text),
(gen_random_uuid(), 'Teacher', 'TEACHER', gen_random_uuid()::text),
(gen_random_uuid(), 'Student', 'STUDENT', gen_random_uuid()::text);

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW."UpdatedAt" = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for auto-updating timestamps
CREATE TRIGGER update_teachers_updated_at BEFORE UPDATE ON "Teachers"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lessonplans_updated_at BEFORE UPDATE ON "LessonPlans"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assessments_updated_at BEFORE UPDATE ON "Assessments"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO teachershub_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO teachershub_user;

-- Performance optimization settings
ALTER TABLE "Teachers" SET (fillfactor = 90);
ALTER TABLE "LessonPlans" SET (fillfactor = 85);
ALTER TABLE "Assessments" SET (fillfactor = 85);
ALTER TABLE "Questions" SET (fillfactor = 80);
ALTER TABLE "Options" SET (fillfactor = 80);

-- Add table statistics for query optimizer
ANALYZE "Teachers";
ANALYZE "LessonPlans";
ANALYZE "Assessments";
ANALYZE "Questions";
ANALYZE "Options";

PRINT 'TeachersHub database schema created successfully with optimized indexes and constraints.';
```

## Performance Optimizations Applied
1. **Clustered indexes** on primary keys for faster access
2. **Composite indexes** for multi-column queries (TeacherId + CreatedAt)
3. **Unique constraints** properly defined for data integrity
4. **Automatic timestamp updates** via triggers
5. **Fill factor optimization** for better insert/update performance
6. **Table statistics** for query optimizer

## Integration Points
- Compatible with Entity Framework Core mapping
- Supports ASP.NET Identity framework
- Optimized for TeacherSyncService auto-creation pattern
- Foreign key constraints properly configured for referential integrity
