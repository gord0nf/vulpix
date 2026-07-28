# configuration

## blueprint

the blueprint is the primary source of truth that acts as a "blueprint" for your system/user. it is
a yaml file (`blueprint.yaml`) located in the config directory. it contains the following
information:

- vulpix settings
- target packages
- target configuration

the vulpix cli applies the blueprint to the system. see `config.default/blueprint.yaml` for an
example.

### yaml schema

```yaml
properties:
    packages:
        type: array
        items:
            type: string
required: [packages]
```
