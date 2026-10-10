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
