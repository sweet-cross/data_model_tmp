# Dimensions

{{ render_dimensions_version_badge() }}

Dimensions are entities that are referenced by other contracts. There are two types
of dimensions:

1. Dimension: Is the the standard dimension used in CROSS. They enforce a hierarchical
structure with top-level entries and more refined categories at the sub-levels.
2. Flexible Dimensions: Are more flexible and custom in the sense that they do not 
have to have a hierarchical structure and allow for arbitrary field names.

The dimension data bundle is versioned as a unit. See
[Versioning](versioning.md) for the bump-rule table and release process.