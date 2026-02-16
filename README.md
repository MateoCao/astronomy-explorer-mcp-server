# 🌌 Astronomy Explorer MCP Server

Servidor [MCP](https://modelcontextprotocol.io/docs/getting-started/intro) (Model Context Protocol) que permite explorar y analizar datos de exoplanetas utilizando el TAP (Table Access Protocol) del [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/).

## Fuente de datos

Los datos provienen del servicio TAP oficial del: 

```bash
https://exoplanetarchive.ipac.caltech.edu/TAP
```
Dataset principal utilizado:
- `pscomppars` (Planetary Systems Composite Parameters)

## Tecnologías usadas
- Python 3.10+
- mcp (FastMCP)
- pyvo (Virtual Observatory client)
- pandas

## Instalación y Configuración

**Requisitos previos**
- Python 3.10+
- Claude Desktop (u otro cliente compatible con MCP)
- Docker (opcional)

1. **Clonar el repositorio**
```bash
git clone https://github.com/MateoCao/astronomy-explorer-mcp-server
cd astronomy-explorer-mcp-server
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate     # Linux / Mac
venv\Scripts\activate        # Windows
```

3. **Instalar dependencias**
```bash
pip install pyvo pandas mcp
```

**Ejecutar manualmente (test rápido)**

Antes de integrarlo a Claude (o al cliente elegido), podés probar que el servidor levanta:
```bash
python server.py
```

### Uso con Docker

1. Construí la imagen

```bash
docker build -t astronomy-explorer-image .
```


**Configuración en Claude Desktop (con docker)**
- Añadí el siguiente bloque a su archivo `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "astronomy-explorer": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "astronomy-explorer-image"
      ]
    }
  }
}
```

### Configuración sin docker

```json
{
  "mcpServers": {
    "astronomy-explorer": {
      "command": "python",
      "args": ["RUTA\\A\\SERVIDOR\\astronomy-explorer-mcp-server\\server.py"]
    }
  }
}
```
📌 Reemplazar la ruta por la ubicación real del archivo.

### Verificación de conexión

Si Claude detecta correctamente el servidor, deberías ver:

- El servidor listado en la sección MCP
- Las herramientas disponibles en el panel

## Arquitectura

El servidor sigue una arquitectura modular orientada a herramientas MCP:

- **FastMCP** como framework de exposición de herramientas
- **TAP (ADQL)** como backend de consultas astronómicas
- **Capa de validación** para parámetros de entrada
- **Capa de ejecución segura** con manejo de errores estructurado
- **Post-procesamiento en Python** para cálculos físicos y métricas derivadas

Las consultas complejas utilizan subqueries para respetar las limitaciones de ordenamiento del estándar ADQL.

## Funcionalidades principales

El servidor expone un set de herramientas dinámicas:

- Explorador de Entidades: Búsqueda profunda por nombre con metadata completa del descubrimiento.

- Análisis de Habitabilidad: Filtros científicos basados en la zona Goldilocks (masa, temperatura de equilibrio y periodo orbital).

- Calculadora de Velocidad de Escape: Implementación de fórmulas físicas para determinar la gravedad superficial y la capacidad de retención atmosférica.

- Estadísticas de Descubrimiento: Análisis por métodos (Tránsito, Velocidad Radial, etc.) y líneas de tiempo históricas.

- Búsqueda Avanzada: Sistema multivariable para investigadores de datos.

Entre otras.

## Formato de respuesta
Todas las herramientas devuelven JSON estrucutrado:

```json
{
  "status": "success",
  "count": 10,
  "data": [...]
}
```

## Ejemplo de uso

**Usuario:**
> ¿Cuál es la velocidad de escape de Kepler-442 b?

**Servidor MCP:**
```json
{
  "pl_name": "Kepler-442 b",
  "velocidad_escape_kms": 13.7,
  "ratio_vs_tierra": 1.22,
  "dificultad_escape": "Difícil de escapar"
}
```

## Notas técnicas

- Se utiliza subquery + `ROWNUM` para respetar ordenamiento en TAP (ADQL aplica `TOP` antes que `ORDER BY`).

- `pl_masse` está en masas terrestres.

- `pl_rade` está en radios terrestres.

- `pl_orbper` está en días.

- `sy_dist` está en parsecs.

## Limitaciones conocidas

- `pl_masse` representa en muchos casos masa mínima (M·sin i), no masa real.
- Los criterios de habitabilidad son aproximaciones físicas simples, no validaciones astrobiológicas.
- El rendimiento depende directamente del servicio TAP externo.
- No hay cache persistente por diseño (consultas siempre actualizadas).


## Futuras mejoras
- Cache local de consultas frecuentes.
- Paginación.
- Integración con matplotlib para generar visualizaciones.

## Contexto científico

Los datos utilizados provienen del [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/) 
una de las fuentes más confiables y actualizadas de información exoplanetaria. 

El proyecto está pensado como una interfaz **exploratoria** y **analítica**, no como una herramienta de validación científica formal.

## Licencia

[MIT](https://choosealicense.com/licenses/mit/)