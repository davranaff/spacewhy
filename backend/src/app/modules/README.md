# Future module contract

Create a business module only after its owner, public contract, authorization scope, and
persistence model are agreed. Keep internals private by default:

    modules/example/
      domain/
      application/
      infrastructure/persistence/
      infrastructure/integrations/
      presentation/http/
      bootstrap.py
      public.py

The dependency direction is presentation to application to domain. Infrastructure adapts ports
owned by application or domain. A module never imports another module's ORM models or
infrastructure; it uses the other module's explicit public contract instead. See
docs/module-template.md for the complete implementation checklist.
