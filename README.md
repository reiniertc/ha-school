# ha-school

Custom Home Assistant integration (HACS) voor Magister (eigen gebruik).

## Installatie (HACS custom repository)
1. Voeg deze repo toe als custom repository in HACS (type: `Integration`).
2. Installeer `ha_school`.
3. Herstart Home Assistant.

## Configuratie (configuration.yaml)

```yaml
ha_school:
  username: !secret magister_username
  password: !secret magister_password
  school: !secret magister_school
  student_id: !secret magister_student_id
  update_interval: 900
```

## Datamodel (Magister app gedrag)
- In deze setup komt "Huiswerk" uit dezelfde afspraken-feed.
- De integratie maakt daarom huiswerk-items op basis van afspraken waar `Inhoud` of `Opmerking` gevuld is.
- Bijlagen-indicatie komt uit `HeeftBijlagen`.

## Let op
- Dit is een onofficiële integratie op basis van reverse engineering.
- Gebruik op eigen risico; endpoint-wijzigingen kunnen de integratie breken.
- Volledige loginflow staat nog op TODO; parsing/mapping voor afspraken+huiswerk is nu wel ingericht.
