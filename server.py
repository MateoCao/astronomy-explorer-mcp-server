from mcp.server.fastmcp import FastMCP
import pyvo as vo
from typing import Optional, List
import json
import pandas as pd
import math

mcp = FastMCP("Astronomy-Explorer")

TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP"

# ============================================================================
# UTILIDADES Y VALIDACIONES
# ============================================================================

def validar_numero_positivo(valor: int, nombre_parametro: str, maximo: int = 1000) -> None:
    """Valida que un número sea positivo y dentro de límites razonables."""
    if valor <= 0:
        raise ValueError(f"{nombre_parametro} debe ser mayor a 0, recibido: {valor}")
    if valor > maximo:
        raise ValueError(f"{nombre_parametro} no puede exceder {maximo}, recibido: {valor}")

def ejecutar_query_segura(query: str, descripcion: str = "consulta") -> str:
    """Ejecuta una query de forma segura con manejo de errores mejorado."""
    try:
        service = vo.dal.TAPService(TAP_URL)
        results = service.search(query)
        df = results.to_table().to_pandas()
        
        if df.empty:
            return json.dumps({
                "status": "empty",
                "message": f"No se encontraron resultados para {descripcion}",
                "data": []
            })
        
        return json.dumps({
            "status": "success",
            "count": len(df),
            "data": json.loads(df.to_json(orient="records"))
        })
    except vo.dal.DALServiceError as e:
        return json.dumps({
            "status": "error",
            "error_type": "service_error",
            "message": f"Error en el servicio TAP: {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown",
            "message": f"Error inesperado: {str(e)}"
        })

# ============================================================================
# FUNCIONES
# ============================================================================

@mcp.tool()
def buscar_datos_exoplaneta(nombre: str) -> str:
    """
    Obtiene información detallada de un exoplaneta específico por su nombre.
    
    Args:
        nombre: Nombre del exoplaneta (ej: "Kepler-442 b", "Proxima Centauri b")
    
    Returns:
        JSON con datos del exoplaneta incluyendo masa, período orbital, método de 
        descubrimiento, facilidad, telescopio, año y ubicación de descubrimiento.
    
    Ejemplo: buscar_datos_exoplaneta("Kepler-442 b")
    """
    if not nombre or not nombre.strip():
        return json.dumps({"status": "error", "message": "El nombre no puede estar vacío"})
    
    # Escapar comillas simples para evitar SQL injection
    nombre_escapado = nombre.replace("'", "''")
    
    query = f"""
    SELECT 
        pl_name, pl_masse, pl_rade, pl_orbper, pl_orbsmax, pl_eqt,
        discoverymethod, disc_year, disc_refname, disc_pubdate, 
        disc_locale, disc_facility, disc_telescope, disc_instrument,
        sy_dist
    FROM pscomppars 
    WHERE pl_name = '{nombre_escapado}'
    """
    
    return ejecutar_query_segura(query, f"exoplaneta '{nombre}'")

@mcp.tool()
def listar_exoplanetas_mas_masivos(numero_planetas: int) -> str:
    """
    Lista los exoplanetas más masivos del universo conocido.
    
    Args:
        numero_planetas: Cantidad de exoplanetas a retornar (máx: 500)
    
    Returns:
        JSON con nombre, masa (en masas terrestres), período orbital y lugar de descubrimiento.
        Nota: 1 masa de Júpiter ≈ 318 masas terrestres
    
    Ejemplo: listar_exoplanetas_mas_masivos(10)
    """
    try:
        validar_numero_positivo(numero_planetas, "numero_planetas", maximo=500)
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)})
    
    query = f"""
    SELECT
        pl_name,
        pl_masse,
        pl_orbper,
        disc_locale,
        disc_year
    FROM (
        SELECT
            pl_name,
            pl_masse,
            pl_orbper,
            disc_locale,
            disc_year
        FROM pscomppars
        WHERE pl_masse IS NOT NULL
        ORDER BY pl_masse DESC
    )
    WHERE ROWNUM <= {numero_planetas}
    """
    
    return ejecutar_query_segura(query, f"top {numero_planetas} exoplanetas más masivos")

@mcp.tool()
def buscar_planetas_habitables(numero_planetas: int = 10) -> str:
    """
    Busca exoplanetas potencialmente habitables en la zona Goldilocks.
    
    Criterios:
    - Masa entre 0.5 y 10 masas terrestres (evita gigantes gaseosos)
    - Período orbital entre 200-500 días (zona habitable tipo Sol)
    - Temperatura de equilibrio entre 200-320K (agua líquida posible)
    
    Args:
        numero_planetas: Cantidad máxima de resultados (máx: 100)
    
    Ejemplo: buscar_planetas_habitables(20)
    """
    try:
        validar_numero_positivo(numero_planetas, "numero_planetas", maximo=100)
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)})
    
    query = f"""
    SELECT
        pl_name,
        pl_masse,
        pl_rade,
        pl_orbper,
        pl_eqt,
        sy_dist,
        disc_year
    FROM (
        SELECT
            pl_name,
            pl_masse,
            pl_rade,
            pl_orbper,
            pl_eqt,
            sy_dist,
            disc_year
        FROM pscomppars
        WHERE pl_masse IS NOT NULL
        AND pl_orbper IS NOT NULL
        AND pl_eqt IS NOT NULL
        AND pl_masse > 0.5
        AND pl_masse < 10.0
        AND pl_orbper > 200.0
        AND pl_orbper < 500.0
        AND pl_eqt > 200
        AND pl_eqt < 320
        ORDER BY ABS(pl_masse - 1.0) ASC
    )
    WHERE ROWNUM <= {numero_planetas}
    """
    
    return ejecutar_query_segura(query, "planetas potencialmente habitables")

@mcp.tool()
def buscar_por_metodo_descubrimiento(metodo: str, limite: int = 20) -> str:
    """
    Busca exoplanetas descubiertos usando un método específico.
    
    Métodos disponibles:
    - "Transit": Tránsito planetario (Kepler, TESS)
    - "Radial Velocity": Velocidad radial (wobble estelar)
    - "Imaging": Imagen directa
    - "Microlensing": Microlente gravitacional
    - "Astrometry": Astrometría
    - "Eclipse Timing Variations": Variaciones de tiempo de eclipse
    
    Args:
        metodo: Método de descubrimiento
        limite: Número máximo de resultados (máx: 200)
    
    Ejemplo: buscar_por_metodo_descubrimiento("Transit", 50)
    """
    try:
        validar_numero_positivo(limite, "limite", maximo=200)
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)})
    
    metodo_escapado = metodo.replace("'", "''")
    
    query = f"""
    SELECT
        pl_name,
        pl_masse,
        pl_rade,
        pl_orbper,
        discoverymethod,
        disc_year,
        disc_facility,
        disc_locale
    FROM (
        SELECT
            pl_name,
            pl_masse,
            pl_rade,
            pl_orbper,
            discoverymethod,
            disc_year,
            disc_facility,
            disc_locale
        FROM pscomppars
        WHERE discoverymethod = '{metodo_escapado}'
        ORDER BY disc_year DESC
    )
    WHERE ROWNUM <= {limite}
    """
    
    return ejecutar_query_segura(query, f"exoplanetas descubiertos por {metodo}")

@mcp.tool()
def timeline_descubrimientos(año_inicio: Optional[int] = None, año_fin: Optional[int] = None) -> str:
    """
    Obtiene estadísticas de descubrimientos de exoplanetas por año.
    
    Args:
        año_inicio: Año de inicio (opcional, default: primer descubrimiento)
        año_fin: Año final (opcional, default: año actual)
    
    Returns:
        JSON con cantidad de descubrimientos por año, método predominante y facilities.
    
    Ejemplo: timeline_descubrimientos(2010, 2020)
    """
    condiciones = []
    if año_inicio:
        condiciones.append(f"disc_year >= {año_inicio}")
    if año_fin:
        condiciones.append(f"disc_year <= {año_fin}")
    
    where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    
    query = f"""
    SELECT
        disc_year,
        COUNT(*) AS num_descubrimientos,
        COUNT(DISTINCT discoverymethod) AS num_metodos,
        COUNT(DISTINCT disc_facility) AS num_facilities
    FROM pscomppars
    {where_clause}
    GROUP BY disc_year
    ORDER BY disc_year ASC
    """
    
    return ejecutar_query_segura(query, "timeline de descubrimientos")

@mcp.tool()
def exoplanetas_mas_cercanos(numero_planetas: int = 10) -> str:
    """
    Lista los exoplanetas más cercanos a la Tierra.
    
    Args:
        numero_planetas: Cantidad de exoplanetas (máx: 100)
    
    Returns:
        JSON con nombre, distancia en parsecs, masa, radio y características.
    
    Ejemplo: exoplanetas_mas_cercanos(15)
    """
    try:
        validar_numero_positivo(numero_planetas, "numero_planetas", maximo=100)
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)})
    
    query = f"""
    SELECT
        pl_name,
        sy_dist,
        pl_masse,
        pl_rade,
        pl_orbper,
        pl_eqt,
        disc_year,
        disc_locale
    FROM (
        SELECT
            pl_name,
            sy_dist,
            pl_masse,
            pl_rade,
            pl_orbper,
            pl_eqt,
            disc_year,
            disc_locale
        FROM pscomppars
        WHERE sy_dist IS NOT NULL
        ORDER BY sy_dist ASC
    )
    WHERE ROWNUM <= {numero_planetas}
    """
    
    return ejecutar_query_segura(query, f"top {numero_planetas} exoplanetas más cercanos")

@mcp.tool()
def busqueda_avanzada(
    masa_min: Optional[float] = None,
    masa_max: Optional[float] = None,
    periodo_min: Optional[float] = None,
    periodo_max: Optional[float] = None,
    distancia_max: Optional[float] = None,
    año_descubrimiento_min: Optional[int] = None,
    metodo: Optional[str] = None,
    locale: Optional[str] = None,
    limite: int = 50
) -> str:
    """
    Búsqueda avanzada con múltiples filtros combinados.
    
    Args:
        masa_min: Masa mínima en masas Terrestres
        masa_max: Masa máxima en masas Terrestres
        periodo_min: Período orbital mínimo en días
        periodo_max: Período orbital máximo en días
        distancia_max: Distancia máxima en parsecs
        año_descubrimiento_min: Año mínimo de descubrimiento
        metodo: Método de descubrimiento
        locale: "Ground" o "Space"
        limite: Número máximo de resultados (máx: 200)
    
    Ejemplo: busqueda_avanzada(masa_min=1, masa_max=10, periodo_min=200, periodo_max=400, locale="Space")
    """
    try:
        validar_numero_positivo(limite, "limite", maximo=200)
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)})
    
    condiciones = []
    
    if masa_min is not None:
        condiciones.append(f"pl_masse >= {masa_min}")
    if masa_max is not None:
        condiciones.append(f"pl_masse <= {masa_max}")
    if periodo_min is not None:
        condiciones.append(f"pl_orbper >= {periodo_min}")
    if periodo_max is not None:
        condiciones.append(f"pl_orbper <= {periodo_max}")
    if distancia_max is not None:
        condiciones.append(f"sy_dist <= {distancia_max}")
    if año_descubrimiento_min is not None:
        condiciones.append(f"disc_year >= {año_descubrimiento_min}")
    if metodo:
        metodo_escapado = metodo.replace("'", "''")
        condiciones.append(f"discoverymethod = '{metodo_escapado}'")
    if locale:
        locale_escapado = locale.replace("'", "''")
        condiciones.append(f"disc_locale = '{locale_escapado}'")
    
    where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    
    query = f"""
    SELECT
        pl_name,
        pl_masse,
        pl_rade,
        pl_orbper,
        sy_dist,
        pl_eqt,
        discoverymethod,
        disc_year,
        disc_locale,
        disc_facility
    FROM (
        SELECT
            pl_name,
            pl_masse,
            pl_rade,
            pl_orbper,
            sy_dist,
            pl_eqt,
            discoverymethod,
            disc_year,
            disc_locale,
            disc_facility
        FROM pscomppars
        {where_clause}
        ORDER BY disc_year DESC
    )
    WHERE ROWNUM <= {limite}
    """
    
    return ejecutar_query_segura(query, "búsqueda avanzada personalizada")

@mcp.tool()
def estadisticas_metodos_descubrimiento() -> str:
    """
    Obtiene estadísticas sobre los métodos de descubrimiento de exoplanetas.
    
    Returns:
        JSON con cada método, cantidad de descubrimientos, y porcentaje del total.
    
    Ejemplo: estadisticas_metodos_descubrimiento()
    """
    query = """
    SELECT
        discoverymethod,
        COUNT(*) AS num_descubrimientos,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS porcentaje
    FROM pscomppars
    WHERE discoverymethod IS NOT NULL
    GROUP BY discoverymethod
    ORDER BY num_descubrimientos DESC
    """
    
    return ejecutar_query_segura(query, "estadísticas de métodos de descubrimiento")

@mcp.tool()
def comparar_con_tierra(nombre_exoplaneta: str) -> str:
    """
    Compara un exoplaneta con la Tierra (masa, radio, período orbital).
    
    Args:
        nombre_exoplaneta: Nombre del exoplaneta a comparar
    
    Returns:
        JSON con datos del exoplaneta comparados con la Tierra.
        - pl_masse está en masas terrestres (1.0 = Tierra)
        - pl_rade está en radios terrestres (1.0 = Tierra)
        - pl_orbper está en días (365.25 = 1 año terrestre)
    
    Ejemplo: comparar_con_tierra("Kepler-442 b")
    """
    if not nombre_exoplaneta or not nombre_exoplaneta.strip():
        return json.dumps({"status": "error", "message": "El nombre no puede estar vacío"})
    
    nombre_escapado = nombre_exoplaneta.replace("'", "''")
    
    # Período orbital de la Tierra
    PERIODO_TIERRA_DIAS = 365.25
    
    query = f"""
    SELECT
        pl_name,
        pl_masse,
        pl_rade,
        pl_orbper,
        pl_eqt,
        sy_dist,
        discoverymethod,
        disc_year,
        disc_locale
    FROM pscomppars
    WHERE pl_name = '{nombre_escapado}'
    """
    
    try:
        service = vo.dal.TAPService(TAP_URL)
        results = service.search(query)
        df = results.to_table().to_pandas()
        
        if df.empty:
            return json.dumps({
                "status": "empty",
                "message": f"No se encontró el exoplaneta '{nombre_exoplaneta}'",
                "data": []
            })
        
        # Hacer los cálculos en Python después de obtener los datos
        data = df.iloc[0].to_dict()
        
        if data['pl_orbper'] is not None and not pd.isna(data['pl_orbper']):
            data['años_terrestres'] = round(data['pl_orbper'] / PERIODO_TIERRA_DIAS, 2)
        else:
            data['años_terrestres'] = None
        
        # Agregar interpretación en texto
        interpretacion = []
        if data['pl_masse'] is not None and not pd.isna(data['pl_masse']):
            if data['pl_masse'] < 0.5:
                interpretacion.append("Planeta muy ligero (posiblemente rocoso pequeño)")
            elif data['pl_masse'] <= 2.0:
                interpretacion.append("Masa similar a la Tierra (super-Tierra)")
            elif data['pl_masse'] <= 10.0:
                interpretacion.append("Mini-Neptuno")
            else:
                interpretacion.append("Gigante gaseoso")
        
        data['interpretacion'] = "; ".join(interpretacion) if interpretacion else None
        
        return json.dumps({
            "status": "success",
            "count": 1,
            "data": [data]
        })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown",
            "message": f"Error inesperado: {str(e)}"
        })
    
@mcp.tool()
def calcular_velocidad_escape(nombre_exoplaneta: str) -> str:
    """
    Calcula la velocidad de escape de un exoplaneta.
    
    La velocidad de escape es la velocidad mínima necesaria para que un objeto
    escape de la atracción gravitacional del planeta sin propulsión adicional.
    
    Fórmula: v_escape = √(2 * G * M / R)
    Donde:
    - G = constante gravitacional = 6.674 × 10^-11 m³/(kg·s²)
    - M = masa del planeta (kg)
    - R = radio del planeta (m)
    
    Args:
        nombre_exoplaneta: Nombre del exoplaneta
    
    Returns:
        JSON con velocidad de escape en km/s, comparación con la Tierra (11.2 km/s),
        y contexto sobre qué significa ese valor.
    
    Ejemplo: calcular_velocidad_escape("Kepler-442 b")
    """
    if not nombre_exoplaneta or not nombre_exoplaneta.strip():
        return json.dumps({"status": "error", "message": "El nombre no puede estar vacío"})
    
    nombre_escapado = nombre_exoplaneta.replace("'", "''")
    
    query = f"""
    SELECT
        pl_name,
        pl_masse,
        pl_rade,
        pl_eqt,
        sy_dist
    FROM pscomppars
    WHERE pl_name = '{nombre_escapado}'
    """
    
    try:
        service = vo.dal.TAPService(TAP_URL)
        results = service.search(query)
        df = results.to_table().to_pandas()
        
        if df.empty:
            return json.dumps({
                "status": "empty",
                "message": f"No se encontró el exoplaneta '{nombre_exoplaneta}'",
                "data": []
            })
        
        data = df.iloc[0].to_dict()
        
        # Verificar que tenemos los datos necesarios
        if pd.isna(data['pl_masse']) or pd.isna(data['pl_rade']):
            return json.dumps({
                "status": "error",
                "message": f"El exoplaneta '{nombre_exoplaneta}' no tiene datos de masa o radio necesarios para calcular velocidad de escape",
                "data": []
            })
        
        # Constantes
        G = 6.674e-11  # m³/(kg·s²) - Constante gravitacional
        MASA_TIERRA_KG = 5.972e24  # kg
        RADIO_TIERRA_M = 6.371e6   # metros
        V_ESCAPE_TIERRA = 11.2     # km/s
        
        # Convertir unidades
        masa_kg = data['pl_masse'] * MASA_TIERRA_KG  # masas terrestres → kg
        radio_m = data['pl_rade'] * RADIO_TIERRA_M   # radios terrestres → metros
        
        # Calcular velocidad de escape: v = √(2*G*M/R)
        v_escape_ms = math.sqrt((2 * G * masa_kg) / radio_m)  # m/s
        v_escape_kms = v_escape_ms / 1000  # km/s
        
        # Comparación con la Tierra
        ratio_tierra = v_escape_kms / V_ESCAPE_TIERRA
        
        # Contexto e interpretación
        interpretacion = []
        
        if v_escape_kms < 5:
            interpretacion.append("Muy baja - atmósfera ligera o inexistente")
            dificultad_escape = "Muy fácil de escapar"
        elif v_escape_kms < 11:
            interpretacion.append("Similar a la Tierra - puede retener atmósfera")
            dificultad_escape = "Moderadamente difícil"
        elif v_escape_kms < 30:
            interpretacion.append("Alta - gravedad superficial significativa")
            dificultad_escape = "Difícil de escapar"
        elif v_escape_kms < 60:
            interpretacion.append("Muy alta - gigante gaseoso pequeño")
            dificultad_escape = "Muy difícil de escapar"
        else:
            interpretacion.append("Extremadamente alta - gigante gaseoso masivo")
            dificultad_escape = "Extremadamente difícil de escapar"
        
        # Comparación con cohetes
        if v_escape_kms < 20:
            interpretacion.append("Un cohete tipo Saturn V podría escapar")
        else:
            interpretacion.append("Requeriría cohetes más potentes que los actuales")
        
        resultado = {
            "pl_name": data['pl_name'],
            "pl_masse": data['pl_masse'],
            "pl_rade": data['pl_rade'],
            "velocidad_escape_kms": round(v_escape_kms, 2),
            "velocidad_escape_tierra": V_ESCAPE_TIERRA,
            "ratio_vs_tierra": round(ratio_tierra, 2),
            "dificultad_escape": dificultad_escape,
            "interpretacion": "; ".join(interpretacion),
            "contexto": {
                "luna": 2.4,  # km/s
                "marte": 5.0,  # km/s
                "tierra": 11.2,  # km/s
                "jupiter": 59.5,  # km/s
                "sol": 617.5  # km/s
            }
        }
        
        return json.dumps({
            "status": "success",
            "count": 1,
            "data": [resultado]
        })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown",
            "message": f"Error inesperado: {str(e)}"
        })

if __name__ == "__main__":
    mcp.run()