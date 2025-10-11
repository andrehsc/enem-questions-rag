# TeachersHub Architecture Documentation

## 1. System Overview

TeachersHub is a modern web application designed to help teachers manage their lesson plans, assessments, and resources. The system follows a multi-tier architecture with clear separation of concerns, implementing Domain-Driven Design (DDD) principles and the Clean Architecture pattern.

## 2. Architecture Diagram

```
┌───────────────┐     ┌────────────────┐     ┌───────────────┐
│               │     │                │     │               │
│    Frontend   │────▶│    Backend     │────▶│   Database    │
│  (React/TS)   │     │  (.NET Core)   │     │  (PostgreSQL) │
│               │     │                │     │               │
└───────────────┘     └────────────────┘     └───────────────┘
       │                      │                      
       │                      │                      
       ▼                      ▼                      
┌───────────────┐     ┌────────────────┐            
│               │     │                │            
│   Nginx Web   │     │  Auth Server   │            
│    Server     │     │   (Node.js)    │            
│               │     │                │            
└───────────────┘     └────────────────┘            
```

## 3. Component Details

### 3.1 Frontend Application

**Technology Stack:**
- React with TypeScript
- Vite as build tool
- Jest for testing
- Nginx as web server

**Key Components:**
- Single Page Application (SPA) architecture
- Component-based UI design
- State management (likely Redux or Context API)
- Responsive design for multiple device sizes

**Deployment:**
- Docker container
- Served via Nginx on port 80, exposed as port 3000

### 3.2 Backend API

**Technology Stack:**
- .NET 8 Web API
- Entity Framework Core
- ASP.NET Core Identity
- PostgreSQL database

**Architecture Pattern:**
The backend follows Clean Architecture with four main layers:

1. **API Layer** (`TeachersHub.Api`)
   - Controllers
   - Middleware
   - API configuration
   - Entry point for HTTP requests

2. **Application Layer** (`TeachersHub.Application`)
   - Use cases/application services
   - Commands and queries (CQRS pattern)
   - DTO models
   - Interfaces for infrastructure services

3. **Domain Layer** (`TeachersHub.Domain`)
   - Business entities
   - Domain rules and logic
   - Value objects
   - Domain events

4. **Infrastructure Layer** (`TeachersHub.Infrastructure`)
   - Data access with Entity Framework Core
   - External service integrations
   - Identity management
   - Data seeding and migrations

**Testing:**
- Unit tests for each layer
- Integration tests
- E2E tests via separate test service

### 3.3 Authentication Server

**Technology Stack:**
- Node.js
- Express
- JWT token-based authentication

**Responsibilities:**
- User authentication
- Token generation and validation
- Rate limiting
- CORS management

### 3.4 Database

**Technology:**
- PostgreSQL 16
- Container-based deployment
- Persistent volume for data storage

**Key Features:**
- Stores user accounts
- Lesson plans
- Assessments
- Teaching resources

## 4. Communication Patterns

### 4.1 Frontend to Backend

- RESTful API calls over HTTP
- JWT-based authentication
- API proxy through Nginx for `/api` routes

### 4.2 Backend to Auth Server

- Direct HTTP calls for token validation
- Shared JWT secret for secure communication

### 4.3 Backend to Database

- Entity Framework Core as ORM
- Connection pooling for performance
- Migrations for schema changes

## 5. Deployment Architecture

TeachersHub uses Docker for containerization and container orchestration:

### 5.1 Containers

- **Frontend Container**: Nginx serving static React files
- **Backend Container**: .NET 8 API with Kestrel server
- **Auth Server Container**: Node.js Express application
- **Database Container**: PostgreSQL 16
- **Test Container**: E2E test environment (activated with profile)

### 5.2 Networking

- Custom Docker network (`teachershub-network`)
- Container-to-container communication
- Port mapping for external access

### 5.3 Health Checks

- Backend: HTTP endpoint `/health`
- Auth Server: HTTP endpoint `/health`
- Database: PostgreSQL readiness check

### 5.4 Volumes

- Persistent storage for PostgreSQL data
- Volume for test reports

## 6. Development Environment

The development environment is set up using Docker Compose with:

- Hot-reloading for frontend
- Database seeding for initial data
- Debug configuration
- Environment variables for local development

## 7. Security Considerations

### 7.1 Authentication

- JWT token-based authentication
- Token expiration (24 hours)
- HTTPS redirect in production
- Secure password storage with ASP.NET Identity

### 7.2 Authorization

- Role-based access control
- Policy-based authorization in .NET
- Frontend route protection

### 7.3 Data Protection

- Connection string security
- Environment-specific secrets
- Parameterized queries via EF Core

## 8. Monitoring and Logging

- Request/response logging middleware
- Health check endpoints
- Docker container logs
- Exception handling middleware

## 9. Future Architecture Considerations

### 9.1 Scaling

- Horizontal scaling of backend and frontend
- Database scaling options
- CDN integration for static assets

### 9.2 Enhancements

- Microservices decomposition
- Event-driven architecture
- API gateway integration
- Caching layer

## 10. Glossary

- **DDD**: Domain-Driven Design
- **JWT**: JSON Web Token
- **SPA**: Single Page Application
- **ORM**: Object-Relational Mapping
- **CQRS**: Command Query Responsibility Segregation