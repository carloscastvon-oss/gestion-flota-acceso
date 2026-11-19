# Gestión de flota y control de acceso vehicular

Aplicación web y móvil en Python y Streamlit, conectada a Supabase (PostgreSQL y Storage), con tres perfiles: Guardia de Garita, Conductor Operativo y Administrador de Puesto de Mando.

## Estructura

```
app/                 Aplicación Streamlit
  main.py            Selección de perfil y navegación por perfil
  config.py          Conexión a Supabase y constantes
  utilidades.py      Normalización de patente y RUT, compresión de fotos
  reportes.py        Guardado de reportes con evidencia fotográfica
  guardia.py         Vista del guardia (patente, validación, registro)
  conductor.py       Vista del conductor (reporte de estado)
  puesto_mando.py    Panel BI del administrador
database/schema.sql  Tablas, restricciones, trigger, RLS y bucket
data/                CSV con el catálogo de vehículos, conductores y autorizaciones
scripts/             Carga de datos y exportación de tablas
docs/                Informe técnico y diagramas
.streamlit/          secrets.toml (local, fuera del repositorio) y su ejemplo
```

## Puesta en marcha

1. Crear un proyecto en Supabase.
2. En el SQL Editor, ejecutar completo `database/schema.sql`. Crea las tablas `vehiculos`, `conductores`, `autorizaciones` y `reportes_estado`, el trigger de mantención y el bucket privado `evidencias-vehiculares` (máximo 800 KB por imagen).
3. Copiar `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completar la URL y la llave secreta del proyecto (Project Settings, API Keys). Este archivo está en `.gitignore`.
4. Instalar dependencias y cargar los datos iniciales:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/cargar_datos.py
```

5. Ejecutar la aplicación desde la raíz del proyecto:

```powershell
streamlit run app/main.py
```

## Perfiles

La aplicación no usa contraseñas. Al abrirla se elige uno de tres perfiles y se muestra solo su vista:

| Perfil | Qué hace | Identificación |
|---|---|---|
| Guardia de Garita | Valida patente y RUT, registra entrada o salida con foto | Ninguna |
| Conductor Operativo | Reporta el estado de sus vehículos autorizados | Su RUT (ejemplo de prueba: 18.234.567-K) |
| Administrador de Puesto de Mando | Panel BI, feed de accesos y auditoría | Ninguna |

## Prueba en móvil

En el navegador de escritorio, abrir las herramientas de desarrollo (F12) y activar la vista de dispositivo móvil. El guardia y el conductor pueden fotografiar con la cámara o adjuntar un archivo.

## Despliegue

En Streamlit Community Cloud, apuntar al archivo `app/main.py` y cargar el contenido de `secrets.toml` en Settings, Secrets.
