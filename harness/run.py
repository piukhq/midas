import typing as t

import click
import toml
from marshmallow import fields, validate, ValidationError
from marshmallow.schema import Schema

class FixtureSchema(Schema):
    slug = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    type = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    firstname = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    lastname = fields.String(required=True, allow_none=False, validate=validate.Length(min=1))
    postcode = fields.String(required=True, allow_none=False)

def load_fixture(fixture_file: t.IO[str]) -> dict:
    content = toml.load(fixture_file)

    try:
        fixture = FixtureSchema().load(content)
    except ValidationError as ex:
        click.secho("Failed to load fixture", fg="red", bold=True)
        raise click.Abort
    return fixture

@click.command()
@click.option(
    "--fixture-file",
    "-f",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True),
    default="harness/fixtures/default.toml",
    show_default=True,
)
def main(fixture_file: t.IO[str],):
    fixture = load_fixture(fixture_file)
    print(fixture)


if __name__ == "__main__":
    main()