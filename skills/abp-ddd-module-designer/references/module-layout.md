# ABP module layout

Consult this when introducing a module or deciding where new files belong. Reuse the repository's project and feature-folder layout; this is a responsibility map, not a required scaffold.

| Project / layer | Typical contents |
| --- | --- |
| Domain.Shared | Shared constants, enums, localization, and error contracts. |
| Domain | Aggregates, entities, value objects, domain services, and custom repository interfaces. |
| Application.Contracts | DTOs and application service interfaces. |
| Application | Use-case orchestration, authorization, and DTO mapping. |
| HttpApi | HTTP exposure through application service contracts, using project controller conventions. |
| EntityFrameworkCore | EF mappings, DbContext integration, and repository implementations. |

Domain must not depend on Application or EntityFrameworkCore. Persistence depends on Domain; HTTP endpoints use application contracts rather than implementation internals.

Create only the components the behavior needs. A domain service is optional, a generic repository may suffice, and HTTP exposure may already be supplied by the project's ABP conventions.

For a reusable module, assess whether a module-specific DbContext interface and implementation are needed. For an existing application, preserve its supported DbContext composition and migration ownership.

Before adding a project, inspect module dependency declarations, package versions, service registration, and host integration. A directory tree alone does not establish a working module.
