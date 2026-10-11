# Base de datos de PHREEQC

`minteq.v4.dat` viene del repositorio oficial de PHREEQC del USGS
(github.com/usgs-coupled/phreeqc3, carpeta `database/`), sin cambios. Deriva de MINTEQA2 v4
(EPA). PHREEQC y sus bases son software y datos del gobierno de EE. UU. en el dominio público.

`pitzer_cu.dat` es `pitzer.dat` de la etiqueta v3.7.3 del mismo repositorio. Se usa esa versión
porque la más reciente no carga en el IPhreeqc 3.7.3 que trae phreeqpy. Lleva un único cambio: un
bloque de cobre, marcado con un comentario, antes del primer `END`. Sus parámetros de Pitzer a
25 °C (Cu-SO4, Cu-HSO4, theta Cu-H y los psi de Cu-H-SO4-HSO4) y la constante de la calcantita vienen
de Justel et al. (2020), ACS Omega 5, 29150, doi:10.1021/acsomega.0c03634, Tablas 3 a 6. Su validez
y sus límites están en `docs/equilibrio.md`.

`cu_h2so4_fuentes.dat` es una base propia, armada con los valores publicados por Fuentes, Justel,
Jimenez y Casas (2023), J. Mol. Liq. 391, 123377, doi:10.1016/j.molliq.2023.123377. Trae sus
constantes de equilibrio (Tabla 5) y sus parámetros de Pitzer con la dependencia con la temperatura
(Tabla 7) para el sistema CuSO4-H2SO4-H2O, de 0 a 100 °C. El modelo del H2SO4 es el de Fuentes y
Casas, ref. [38] del artículo.

Única corrección: los coeficientes de la Tabla 5 están redondeados a 3 cifras y dan otro log K a
25 °C, hasta 3,6 unidades de diferencia. Se corrigió solo el término constante (A1) de cada uno,
para respetar el log K a 298,15 K que tabula el mismo artículo; cada corrección queda anotada en la
base. El artículo no es de acceso abierto y no se incluye; solo se usan sus valores, citados.
