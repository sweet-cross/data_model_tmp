# Dimensions

{{ render_dimensions_version_badge() }}

Dimensions define the indexes over which variables (assumptions and results) are specified, such as region, fuel, technology, and many others. CROSS distinguishes between two types of dimensions:

1. **[Standard Dimensions](dimensions/index.md)**

    The core dimensions used throughout CROSS. They follow a hierarchical structure, with top-level entries that can be subdivided into more specific levels (for example, a fuel category can be broken down into individual fuels). Standard dimensions use a fixed schema consisting of
   `id`, `level`, `parent_id`, `label`, `description`.

2. **[Flexible Dimensions](flexible/index.md)**

    Dimensions that do not follow a hierarchical structure and are therefore not constrained to the standard dimension schema. Their fields are defined according to the specific requirements of each dimension.

The complete set of dimensions is versioned as a single data bundle. See
[Versioning](versioning.md) for the versioning rules and release process.