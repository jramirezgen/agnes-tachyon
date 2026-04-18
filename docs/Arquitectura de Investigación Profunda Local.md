# **Arquitectura de Sistemas Cognitivos Autónomos para Investigación Profunda en Entornos Locales: Un Paradigma de Orquestación, Ética y Persistencia**

## **1\. Introducción y Marco Conceptual**

La evolución de la inteligencia artificial generativa ha precipitado un cambio de paradigma fundamental en la interacción humano-computadora, transitando desde modelos de respuesta estática hacia agentes cognitivos dinámicos capaces de ejecutar tareas complejas de larga duración. En este contexto, el concepto de "Deep Research" o Investigación Profunda emerge no como una simple mejora de la búsqueda web tradicional, sino como una arquitectura cognitiva distinta que simula los procesos de razonamiento, planificación y síntesis de un analista humano experto. A diferencia de los sistemas de Generación Aumentada por Recuperación (RAG) convencionales, que operan bajo un flujo lineal de "recuperar y generar", los sistemas de investigación profunda requieren ciclos iterativos de exploración, evaluación de hipótesis y refinamiento de estrategias de búsqueda.

La implementación de tales capacidades en una infraestructura local presenta un desafío de ingeniería y diseño de sistemas formidable. La exigencia de operar "on-premise" o localmente responde a imperativos críticos de soberanía de datos, privacidad y control de costos, eliminando la dependencia de APIs en la nube que pueden comprometer información sensible o imponer latencias inaceptables. Sin embargo, esta restricción traslada la carga computacional y la complejidad de orquestación al hardware del usuario final, requiriendo una optimización meticulosa de recursos finitos como la memoria de video (VRAM) y el ancho de banda de procesamiento.

Este informe técnico desarrolla una validación exhaustiva de la arquitectura óptima para un módulo de Deep Research local. El análisis desglosa la arquitectura en cuatro pilares fundamentales: la orquestación agéntica basada en grafos de estado, la adquisición de datos mediante técnicas de scraping ético y visión computacional, la validación cognitiva para asegurar la integridad fáctica, y la gestión de memoria incremental mediante bases de datos vectoriales sin servidor y estándares de objetos de investigación. A través de la síntesis de evidencia técnica reciente, se propone un diseño que integra **LangGraph** como motor de razonamiento cíclico, **Crawl4AI** y **OmniParser** para la percepción multimodal, protocolos **Chain of Verification (CoVe)** para la robustez epistémica, y **LanceDB** junto con **RO-Crate** para la persistencia del conocimiento a largo plazo.

## ---

**2\. Orquestación Agéntica: Del Flujo Lineal a los Grafos de Estado**

La orquestación es el componente arquitectónico que define la topología de la cognición del agente. En un sistema de investigación profunda, la orquestación no puede limitarse a una secuencia predeterminada de pasos; debe permitir la adaptabilidad, el retroceso y la reevaluación. El debate actual en la ingeniería de sistemas agénticos se centra en la dicotomía entre marcos centrados en datos y marcos centrados en el control de flujo.

### **2.1. Evaluación Comparativa: LangGraph frente a LlamaIndex Workflows**

La selección del marco de orquestación es la decisión fundacional del diseño del sistema. El análisis de la literatura técnica revela una distinción clara entre **LangGraph** y **LlamaIndex**, dos de los ecosistemas más prominentes en el desarrollo de aplicaciones LLM. Mientras que ambos frameworks han convergido hacia capacidades agénticas, sus filosofías subyacentes dictan su idoneidad para la investigación profunda autónoma.1

LlamaIndex, originado como un marco de datos ("Data Framework"), sobresale en la ingestión, indexación y recuperación de información. Sus flujos de trabajo son excepcionales para pipelines de RAG sobre documentos estáticos, donde el objetivo principal es conectar un modelo de lenguaje con fuentes de datos propietarias. Sin embargo, la investigación profunda es intrínsecamente un proceso de navegación y toma de decisiones, no solo de recuperación. Los flujos de trabajo predeterminados en LlamaIndex tienden a ser apátridas (stateless) o gestionar el estado de manera implícita a través de contextos de recuperación, lo que limita la capacidad de modelar comportamientos complejos de "viaje en el tiempo" o ramificaciones condicionales profundas necesarias para la investigación iterativa.3

Por el contrario, **LangGraph** se ha diseñado desde sus cimientos como un marco de orquestación de bajo nivel que modela las interacciones del agente como un grafo cíclico dirigido y con estado (Stateful Directed Cyclic Graph). Esta arquitectura permite definir nodos como funciones de procesamiento y bordes como transiciones de control, donde el estado global del grafo se mantiene y actualiza explícitamente en cada paso. Esta persistencia del estado es crítica para aplicaciones de larga ejecución ("long-running processes"), permitiendo funcionalidades como la pausa para intervención humana (human-in-the-loop), la recuperación ante fallos y la introspección del historial de ejecución.1

La validación técnica sugiere que, para un módulo de investigación profunda local que debe operar de manera autónoma, **LangGraph** ofrece la granularidad de control necesaria. La capacidad de definir ciclos explícitos es fundamental: un agente investigador debe poder formular una hipótesis, buscar evidencia, evaluar la calidad de los resultados y, si la evidencia es insuficiente, regresar al paso de formulación de hipótesis sin perder el contexto de lo que ya ha intentado. LlamaIndex, aunque potente en la capa de datos, requiere abstracciones adicionales para manejar esta lógica de estado compleja de manera transparente.4

### **2.2. Arquitectura de Referencia: Implementación del Patrón STORM**

La arquitectura óptima para la investigación profunda se basa en el patrón **STORM** (Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking), una metodología que simula el proceso de redacción colaborativa de artículos enciclopédicos. La adaptación de este patrón a un entorno local mediante LangGraph permite descomponer la tarea monolítica de "investigar un tema" en una serie de operaciones especializadas coordinadas.7

El diseño arquitectónico validado se estructura en torno a un grafo de estado que coordina múltiples agentes especializados, cada uno responsable de una faceta del proceso de investigación. Este enfoque modular no solo mejora la calidad del resultado final al introducir diversidad de perspectivas, sino que también optimiza el uso de recursos locales al permitir la carga y descarga dinámica de modelos o herramientas específicas para cada nodo del grafo.

#### **2.2.1. Fase de Descubrimiento de Perspectivas y Planificación**

El proceso inicia no con una búsqueda ciega, sino con una fase de planificación estratégica. Un nodo inicial, denominado "Generador de Perspectivas", utiliza el modelo de lenguaje local para analizar la consulta del usuario y generar una lista de "personas" o roles expertos que podrían aportar puntos de vista únicos sobre el tema. Por ejemplo, ante una consulta sobre "Criptomonedas y Sostenibilidad", el sistema podría instanciar personas como un "Ingeniero Ambiental", un "Economista Financiero" y un "Desarrollador de Blockchain".

Esta fase es crucial para mitigar los sesgos inherentes del modelo de lenguaje y asegurar una cobertura exhaustiva del tema. En LangGraph, esto se implementa como un nodo que recibe el estado inicial (la consulta) y actualiza el estado con una lista de objetos "Persona". Posteriormente, un nodo de "Entrevista" orquesta conversaciones simuladas entre un agente entrevistador y estas personas. El entrevistador formula preguntas incisivas basadas en la perspectiva del rol, y el agente utiliza herramientas de búsqueda para fundamentar las respuestas en datos reales recuperados de la web.10

#### **2.2.2. El Bucle de Investigación Iterativa**

El núcleo del sistema es un sub-grafo cíclico que gestiona la expansión de conocimientos. Basándose en las entrevistas simuladas, un nodo "Editor de Esquemas" genera una estructura jerárquica (outline) para el reporte final. Cada sección de este esquema se convierte en una tarea de investigación independiente.

Aquí, la arquitectura de LangGraph demuestra su superioridad al permitir la ejecución paralela o secuencial de sub-grafos de investigación para cada sección. Un nodo de "Expansión de Consultas" transforma los títulos de las secciones en múltiples consultas de búsqueda optimizadas para motores de búsqueda semántica o por palabras clave. Los resultados se procesan en un nodo de "Lectura y Síntesis", que extrae citas relevantes y las asocia a la sección correspondiente en el estado compartido.12

Crucialmente, el sistema integra un nodo de "Reflexión". Antes de considerar una sección como completa, el agente evalúa si la información recopilada es suficiente y coherente. Si detecta lagunas o contradicciones, el flujo se redirige hacia atrás en el grafo, activando nuevas búsquedas con parámetros refinados. Este bucle de retroalimentación (feedback loop) es la esencia de la investigación profunda y es impracticable en arquitecturas lineales simples.13

#### **2.2.3. Síntesis y Escritura Colaborativa Virtual**

La fase final implica la compilación de la información en un documento coherente. Un nodo "Escritor" toma el esquema y las citas recopiladas para redactar el contenido, asegurando que cada afirmación esté respaldada por una referencia explícita almacenada en el estado. En un diseño avanzado, se puede implementar un ciclo de revisión donde un segundo agente "Revisor" critica el borrador buscando falacias lógicas o falta de fluidez, solicitando reescrituras al nodo Escritor hasta satisfacer criterios de calidad predefinidos.

### **2.3. Sinergia Arquitectónica: LlamaIndex como Capa de Datos**

Aunque LangGraph gestiona la orquestación, LlamaIndex desempeña un papel vital como la capa de gestión de datos (Data Layer) dentro de los nodos del grafo. La arquitectura validada propone encapsular las capacidades de ingestión y recuperación de LlamaIndex dentro de las herramientas que utilizan los agentes de LangGraph. Por ejemplo, cuando un agente descarga documentos extensos, LlamaIndex puede utilizare para indexar estos documentos localmente en tiempo real, permitiendo al agente realizar consultas RAG precisas sobre el material recién adquirido ("Retrieve-on-the-fly") en lugar de intentar procesar todo el texto crudo en la ventana de contexto del LLM.1 Esta integración híbrida aprovecha la robustez de LlamaIndex para el manejo de datos y la flexibilidad de LangGraph para la lógica de control, ofreciendo lo que se ha denominado "lo mejor de ambos mundos" en la ingeniería de sistemas agénticos.1

La siguiente tabla resume la comparativa funcional que justifica esta elección arquitectónica:

| Característica | LangGraph | LlamaIndex Workflows | Implicación para Deep Research Local |
| :---- | :---- | :---- | :---- |
| **Modelo Mental** | Grafo de Estado Cíclico | Pipeline de Datos Dirigido | LangGraph permite bucles de investigación ("intentar hasta lograr") esenciales para la autonomía. |
| **Gestión de Estado** | Explícita, tipada y persistente | Implícita o centrada en contexto | La persistencia explícita de LangGraph es vital para investigaciones largas que pueden pausarse o auditarse. |
| **Flexibilidad** | Alta (código de bajo nivel) | Media (abstracciones de alto nivel) | LangGraph permite personalizar la lógica de decisión de cada paso, crucial para agentes especializados. |
| **Manejo de Datos** | Básico (depende de integración) | Avanzado (nativo) | LlamaIndex debe integrarse como la biblioteca de herramientas de datos dentro de los nodos de LangGraph. |

## ---

**3\. Adquisición de Datos: Scraping Ético, Visión y Ejecución Local**

La capacidad de un agente de investigación para interactuar con la web ("World Wide Web") es su sentido principal. En un entorno local, esta capacidad debe ser autónoma, resistente a la complejidad de la web moderna y respetuosa con las normas de acceso, todo ello sin depender de servicios de extracción en la nube que comprometan la privacidad o impongan costos recurrentes.

### **3.1. Paradigmas de Extracción: Automatización vs. Interpretación Semántica**

La adquisición de datos web ha evolucionado desde el simple análisis sintáctico de HTML hacia la interpretación semántica y visual. La elección de la herramienta de scraping adecuada tiene un impacto directo en la calidad de la información que ingresa al sistema y en la eficiencia del consumo de tokens del modelo de lenguaje.

#### **3.1.1. Limitaciones de la Automatización de Navegadores Tradicional**

Herramientas de automatización de navegadores como **Playwright** y **Puppeteer** han sido estándares de la industria para pruebas y scraping de sitios dinámicos (SPA). Permiten controlar una instancia real de Chrome o Firefox, ejecutando JavaScript y renderizando el DOM completo. Sin embargo, su integración en flujos de trabajo de IA presenta fricciones significativas.15

En primer lugar, la salida de estas herramientas suele ser HTML crudo o texto extraído sin estructura semántica clara. Esto obliga al modelo de lenguaje a "limpiar" el ruido (menús, anuncios, scripts) gastando valiosos recursos de contexto. En segundo lugar, la ejecución de navegadores en modo "headless" (sin interfaz gráfica) en entornos locales como WSL2 (Windows Subsystem for Linux) es notoriamente compleja. Requiere la configuración de servidores de visualización virtual como **Xvfb** (X Virtual Framebuffer) o la redirección de la salida gráfica a servidores X en Windows como **VcXsrv** para depuración. Errores comunes relacionados con la falta de librerías gráficas o configuraciones de pantalla incorrectas pueden hacer que el despliegue local sea frágil y difícil de mantener.17 Además, la dependencia de selectores CSS o XPath rígidos hace que los scripts sean vulnerables a cambios menores en el diseño de las páginas web, rompiendo el pipeline de investigación frecuentemente.

#### **3.1.2. La Revolución del Scraping Nativo de IA: Crawl4AI**

Frente a estas limitaciones, ha surgido una nueva categoría de herramientas diseñadas específicamente para alimentar sistemas de IA, liderada por **Crawl4AI** y **Firecrawl**. La validación técnica posiciona a **Crawl4AI** como la solución superior para despliegues locales y de código abierto.15

Crawl4AI se distingue por su capacidad de procesar páginas web complejas y convertirlas directamente a **Markdown** limpio, un formato que los LLMs "entienden" nativamente mucho mejor que el HTML. Esta conversión no es trivial; implica identificar algoritmicamente el contenido principal, preservar la jerarquía de encabezados, formatear tablas y filtrar elementos irrelevantes. Al realizar este pre-procesamiento, Crawl4AI reduce drásticamente la cantidad de tokens que el agente debe leer, acelerando la inferencia y reduciendo costos computacionales.21

Además, Crawl4AI es compatible con la ejecución local, permitiendo utilizar el navegador del usuario o una instancia controlada sin necesidad de enviar URLs a una API de terceros, garantizando la privacidad absoluta de la investigación. Su arquitectura asíncrona y capacidad de manejar múltiples pestañas simultáneamente se alinean perfectamente con la ejecución paralela de nodos en LangGraph.

### **3.2. Visión Computacional para la Web: OmniParser**

La web es un medio visual. Gran cantidad de información crítica reside en gráficos, infografías, interfaces de usuario complejas y documentos PDF que el scraping textual ignora o malinterpreta. Para un módulo de investigación profunda verdaderamente capaz, se requiere una capacidad de "ver" y entender la pantalla.

**Microsoft OmniParser V2** se ha validado como el estado del arte para esta tarea en entornos locales. A diferencia de los modelos de visión generalistas que pueden describir una imagen ("un gráfico de barras"), OmniParser está entrenado para analizar capturas de pantalla de interfaces de usuario, descomponiéndolas en elementos estructurados e interactuables.22 Esto permite al agente no solo "leer" una página web visualmente compleja, sino también entender la funcionalidad de sus elementos (botones, menús, iconos), lo cual es esencial si el agente necesita navegar a través de aplicaciones web sofisticadas para encontrar datos.

Sin embargo, la integración de OmniParser en un entorno local impone requisitos de hardware significativos. Las pruebas de rendimiento indican que la ejecución fluida de los modelos de detección y descripción de OmniParser puede demandar entre **10 y 12 GB de VRAM** dedicada.24 Para sistemas con recursos limitados (ej. tarjetas de 8GB), es imperativo implementar técnicas de optimización como la cuantización de modelos a 4 bits o la descarga parcial de capas a la CPU (CPU offloading), aunque esto conlleva una penalización en la latencia.25

Alternativas más ligeras como **Qwen-VL** o modelos especializados de menor tamaño pueden considerarse para tareas de visión menos críticas, pero OmniParser ofrece la mayor precisión en la interpretación de la semántica de la interfaz de usuario, reduciendo las alucinaciones visuales donde el modelo "imagina" botones o textos que no existen.27

### **3.3. Ética y Responsabilidad en la Adquisición de Datos**

Un sistema de investigación automatizado potente conlleva la responsabilidad de operar éticamente dentro del ecosistema web. El scraping agresivo o no regulado puede degradar el servicio de los sitios web objetivo y violar términos de uso, resultando en bloqueos de IP que inutilizan al agente.

#### **3.3.1. Cumplimiento Normativo Automatizado**

El diseño del módulo debe integrar un middleware de cumplimiento ético que verifique automáticamente el archivo **robots.txt** de cada dominio antes de realizar cualquier extracción. Librerías de análisis de exclusión de robots deben ser parte integral del nodo de herramienta de búsqueda en LangGraph. Si un sitio prohíbe explícitamente el scraping por bots (User-Agent: \* Disallow: /), el agente debe estar programado para respetar esta directiva y buscar fuentes alternativas, registrando el evento en su memoria de auditoría.15

#### **3.3.2. Estrategias de Cortesía (Politeness)**

Para evitar ser detectado como un ataque de denegación de servicio (DoS), el sistema debe implementar límites de tasa (rate limiting) y esperas aleatorias (jitter) entre solicitudes al mismo dominio. Crawl4AI y otras herramientas modernas permiten configurar estos parámetros. Además, es una práctica recomendada que el agente se identifique honestamente a través de su cadena de User-Agent, proporcionando potencialmente una URL de contacto o descripción del propósito de la investigación, fomentando la transparencia.15

## ---

**4\. Validación Cognitiva: Integridad Fáctica y Verificación**

La propensión de los modelos de lenguaje grandes a la "alucinación"—la generación de información plausible pero falsa—es el talón de Aquiles de cualquier sistema de investigación automatizada. En un contexto profesional, un dato incorrecto puede invalidar un informe completo. Por lo tanto, la arquitectura no puede confiar ciegamente en la generación del LLM; debe incorporar capas de verificación explícita.

### **4.1. Protocolo Chain of Verification (CoVe)**

El método **Chain of Verification (CoVe)** representa un avance metodológico significativo para mitigar alucinaciones. En lugar de generar la respuesta final en un solo paso, CoVe descompone el proceso en cuatro etapas distintas, forzando al modelo a auditar su propio razonamiento.29

1. **Generación de Respuesta Base:** El agente genera un borrador inicial basado en su entrenamiento y los datos recuperados.  
2. **Planificación de Verificaciones:** El modelo analiza su propio borrador para identificar afirmaciones fácticas verificables (ej. fechas, cifras, nombres). Genera una lista de preguntas de verificación independientes diseñadas para confirmar o refutar estos puntos (ej. "¿Fue la empresa X adquirida en 2020?").  
3. **Ejecución de Verificaciones:** El agente ejecuta estas preguntas contra el motor de búsqueda o su base de conocimientos local, obteniendo respuestas frescas y no sesgadas por el contexto del borrador original.  
4. **Revisión y Refinamiento:** Finalmente, el agente compara las respuestas de verificación con el borrador original. Si se detectan inconsistencias, el texto se corrige.

La validación técnica sugiere implementar la variante **"Factored \+ Revise"** de CoVe, donde cada pregunta de verificación se responde de manera independiente antes de la revisión final. Esto evita que el modelo confunda el contexto de múltiples verificaciones simultáneas y mejora la precisión de la corrección.31 En LangGraph, este protocolo se modela como un sub-grafo de validación que se inserta entre la fase de escritura y la entrega final del reporte.

### **4.2. Fact-Checking Automatizado y Descomposición de Reclamos**

Para fortalecer aún más la integridad, se recomienda la integración de bibliotecas especializadas en fact-checking como **OpenFactCheck** o la implementación de lógica personalizada de descomposición de reclamos. Este enfoque implica dividir oraciones complejas en unidades atómicas de información (reclamos individuales) que pueden ser verificadas binariamente (Verdadero/Falso/No concluyente).33

Por ejemplo, la oración "El fármaco X, aprobado en 2019, redujo la mortalidad en un 50%" se descompone en:

* Reclamo A: "El fármaco X fue aprobado en 2019".  
* Reclamo B: "El fármaco X reduce la mortalidad".  
* Reclamo C: "La reducción de mortalidad es del 50%".

Cada reclamo atómico se somete a una búsqueda de evidencia. Si la evidencia contradice un reclamo, el sistema no solo corrige el texto, sino que puede añadir una nota al pie o una sección de "Discrepancias en las Fuentes", elevando la calidad analítica del reporte al exponer la incertidumbre o el conflicto en los datos, una característica valorada en la investigación profesional.35

## ---

**5\. Memoria Incremental y Persistencia del Conocimiento**

Una diferencia clave entre un chat y una investigación profunda es la dimensión temporal y acumulativa del conocimiento. El sistema debe ser capaz de recordar lo que investigó ayer para construir sobre ello hoy, sin tener que re-procesar toda la información cruda. Esto requiere una arquitectura de memoria robusta y estructurada.

### **5.1. Almacenamiento Vectorial: La Superioridad de LanceDB**

La elección de la base de datos vectorial es crítica para el rendimiento local. Mientras que soluciones como ChromaDB son populares para prototipos, el análisis arquitectónico favorece decididamente a **LanceDB** para sistemas de producción local.37

LanceDB se diferencia por ser una base de datos "serverless" y embebida que opera directamente sobre el sistema de archivos utilizando el formato de datos **Lance**. Lance es un formato columnar moderno optimizado para datos multimodales y acceso aleatorio rápido. A diferencia de las bases de datos que requieren cargar índices masivos en la memoria RAM (lo cual es prohibitivo cuando la base de conocimientos crece a gigabytes o terabytes), LanceDB permite realizar búsquedas vectoriales y filtrados de metadatos con un consumo de memoria mínimo, cargando solo las páginas de datos necesarias desde el disco (SSD/NVMe).39

Además, LanceDB soporta nativamente el almacenamiento de vectores multimodales (texto e imagen en el mismo espacio latente) y ofrece capacidades de versionado de tablas al estilo Git. Esto último es fundamental para la investigación incremental: permite al agente crear "ramas" de conocimiento, experimentar con nuevas fuentes y, si es necesario, revertir la base de datos a un estado anterior limpio, garantizando la higiene de los datos a largo plazo.41

### **5.2. Estandarización de Datos: RO-Crate y JSON-LD**

Guardar vectores no es suficiente; se debe preservar el contexto y la procedencia de la información. Para ello, se valida el uso del estándar **RO-Crate (Research Object Crate)**. Un RO-Crate es un método ligero y basado en estándares abiertos para empaquetar datos de investigación junto con sus metadatos.43

En la arquitectura propuesta, cada "proyecto de investigación" se guarda como un directorio RO-Crate. Este directorio contiene los archivos crudos (PDFs descargados, imágenes, esquemas Markdown) y un archivo ro-crate-metadata.json. Este archivo JSON-LD (Linked Data) describe semánticamente las relaciones entre los archivos: quién (qué agente) recuperó el dato, cuándo, desde qué URL, y cómo se relaciona con otros datos.45

La adopción de RO-Crate transforma el almacenamiento pasivo en una **Memoria Semántica Activa**. Permite que el sistema responda preguntas sobre su propio proceso de investigación ("¿Qué fuentes consultaste para la sección de economía la semana pasada?") y facilita la interoperabilidad, permitiendo que el paquete de investigación sea compartido, archivado o publicado manteniendo toda su trazabilidad y reproducibilidad científica.47

## ---

**6\. Implementación de Infraestructura y Hardware Local**

La viabilidad de esta arquitectura depende de su ejecución eficiente en hardware accesible. A continuación, se detallan las consideraciones de implementación para entornos de consumidor de alto rendimiento (workstations).

### **6.1. Gestión de Recursos y Estrategia de Descarga (Offloading)**

El cuello de botella principal en la ejecución local es la VRAM. Ejecutar un LLM competente (como Llama-3-70B cuantizado o Qwen-2.5-32B) junto con un modelo de visión (OmniParser) y un modelo de embeddings simultáneamente puede saturar fácilmente 24GB de VRAM (e.g., NVIDIA RTX 3090/4090).

La estrategia validada es la **gestión dinámica de carga de modelos**. El orquestador LangGraph debe gestionar el ciclo de vida de los modelos:

* **Fase de Texto:** Durante la planificación y redacción, el modelo de visión se descarga completamente de la GPU, liberando espacio para cargar un LLM con mayor ventana de contexto (context window), crucial para sintetizar grandes volúmenes de texto.  
* **Fase de Visión:** Cuando el scraper detecta contenido visual crítico, el sistema pausa el LLM principal, descarga sus pesos o los mueve a la RAM del sistema (CPU offloading), y carga OmniParser en la GPU para procesar las imágenes. Una vez extraída la información estructurada, se invierte el proceso.25

El uso de formatos cuantizados como **GGUF** (para ejecución en CPU+GPU vía llama.cpp) o **AWQ/GPTQ** (para ejecución pura en GPU) es obligatorio. Las pruebas demuestran que la cuantización a 4-bit (Q4\_K\_M) ofrece un compromiso óptimo, reduciendo el uso de memoria a la mitad con una degradación mínima en la capacidad de razonamiento, permitiendo ejecutar modelos de 70B parámetros en configuraciones de doble GPU o modelos de 30B en una sola tarjeta de gama alta.49

### **6.2. Stack Tecnológico Integrado**

La arquitectura recomendada se consolida en el siguiente stack tecnológico:

* **Orquestación:** Python 3.10+ con **LangGraph** para la lógica de control y estado.  
* **Motor de Inferencia LLM:** **vLLM** (para alto rendimiento en Linux/WSL2) o **Ollama** (para facilidad de uso y gestión de modelos GGUF).  
* **Recuperación y Datos:** **LlamaIndex** integrado como librería de herramientas dentro de los nodos de LangGraph.  
* **Scraping:** **Crawl4AI** ejecutándose en contenedor Docker para aislamiento y manejo de dependencias de navegador.  
* **Visión:** **OmniParser V2** servido como microservicio API local (para facilitar la gestión independiente de su ciclo de vida y recursos).  
* **Memoria:** **LanceDB** para almacenamiento vectorial y **RO-Crate** para estructuración de metadatos y archivos.

### **6.3. Conclusión**

La arquitectura validada para el módulo de Deep Research local representa un ecosistema sofisticado donde la orquestación cíclica de **LangGraph**, la percepción precisa de **Crawl4AI** y **OmniParser**, la integridad verificada por **CoVe**, y la memoria persistente de **LanceDB** convergen para crear un analista artificial autónomo. Este diseño no solo satisface los requisitos funcionales de investigación profunda, sino que respeta rigurosamente las restricciones éticas y de privacidad inherentes a la operación local, estableciendo un nuevo estándar para asistentes cognitivos soberanos.

#### **Obras citadas**

1. LLamaIndex vs LangGraph: Comparing LLM Frameworks \- TrueFoundry, fecha de acceso: enero 25, 2026, [https://www.truefoundry.com/blog/llamaindex-vs-langgraph](https://www.truefoundry.com/blog/llamaindex-vs-langgraph)  
2. LlamaIndex vs LangGraph: How are They Different? \- ZenML Blog, fecha de acceso: enero 25, 2026, [https://www.zenml.io/blog/llamaindex-vs-langgraph](https://www.zenml.io/blog/llamaindex-vs-langgraph)  
3. LangChain vs LangGraph vs LlamaIndex: Best LLM framework \- Xenoss, fecha de acceso: enero 25, 2026, [https://xenoss.io/blog/langchain-langgraph-llamaindex-llm-frameworks](https://xenoss.io/blog/langchain-langgraph-llamaindex-llm-frameworks)  
4. What are pros and cons of Lang graph vs Llama index Multiple Agent systems \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/LangChain/comments/1fs3qn9/what\_are\_pros\_and\_cons\_of\_lang\_graph\_vs\_llama/](https://www.reddit.com/r/LangChain/comments/1fs3qn9/what_are_pros_and_cons_of_lang_graph_vs_llama/)  
5. LangGraph overview \- Docs by LangChain, fecha de acceso: enero 25, 2026, [https://docs.langchain.com/oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview)  
6. LangChain vs LlamaIndex (2025) — Which One is Better? | by Pedro Azevedo \- Medium, fecha de acceso: enero 25, 2026, [https://medium.com/@pedroazevedo6/langgraph-vs-llamaindex-workflows-for-building-agents-the-final-no-bs-guide-2025-11445ef6fadc](https://medium.com/@pedroazevedo6/langgraph-vs-llamaindex-workflows-for-building-agents-the-final-no-bs-guide-2025-11445ef6fadc)  
7. How does this Compare to Storm? · assafelovic gpt-researcher · Discussion \#999 \- GitHub, fecha de acceso: enero 25, 2026, [https://github.com/assafelovic/gpt-researcher/discussions/999](https://github.com/assafelovic/gpt-researcher/discussions/999)  
8. stanford-oval/storm: An LLM-powered knowledge curation system that researches a topic and generates a full-length report with citations. \- GitHub, fecha de acceso: enero 25, 2026, [https://github.com/stanford-oval/storm](https://github.com/stanford-oval/storm)  
9. Building STORM from scratch with LangGraph \- YouTube, fecha de acceso: enero 25, 2026, [https://www.youtube.com/watch?v=1uUORSZwTz4](https://www.youtube.com/watch?v=1uUORSZwTz4)  
10. Build a STORM Research Assistant using LangGraph : r/LangChain \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/LangChain/comments/1l4nsps/build\_a\_storm\_research\_assistant\_using\_langgraph/](https://www.reddit.com/r/LangChain/comments/1l4nsps/build_a_storm_research_assistant_using_langgraph/)  
11. How to Build the Ultimate AI Automation with Multi-Agent Collaboration \- LangChain Blog, fecha de acceso: enero 25, 2026, [https://blog.langchain.com/how-to-build-the-ultimate-ai-automation-with-multi-agent-collaboration/](https://blog.langchain.com/how-to-build-the-ultimate-ai-automation-with-multi-agent-collaboration/)  
12. Building a Deep Research Agent with LangGraph (0.6.7) | by Pavan Nagula | Medium, fecha de acceso: enero 25, 2026, [https://medium.com/@pavan.nagula/building-a-deep-research-agent-with-langgraph-0-6-7-1904b4c8a620](https://medium.com/@pavan.nagula/building-a-deep-research-agent-with-langgraph-0-6-7-1904b4c8a620)  
13. LangGraph 101: Let's Build A Deep Research Agent | Towards Data Science, fecha de acceso: enero 25, 2026, [https://towardsdatascience.com/langgraph-101-lets-build-a-deep-research-agent/](https://towardsdatascience.com/langgraph-101-lets-build-a-deep-research-agent/)  
14. ReAct in AI Agents: Designing Intelligent Systems with LangChain, LangGraph, and some Agentic Patterns | by Rashmi Achar | Medium, fecha de acceso: enero 25, 2026, [https://medium.com/@rashmi.achar86/react-in-ai-agents-designing-intelligent-systems-with-langchain-langgraph-and-some-agentic-571fcc056afe](https://medium.com/@rashmi.achar86/react-in-ai-agents-designing-intelligent-systems-with-langchain-langgraph-and-some-agentic-571fcc056afe)  
15. Best Open-Source Web Crawlers in 2026 \- Firecrawl, fecha de acceso: enero 25, 2026, [https://www.firecrawl.dev/blog/best-open-source-web-crawler](https://www.firecrawl.dev/blog/best-open-source-web-crawler)  
16. What are people actually using for web scraping that doesn't break every few weeks?, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/AI\_Agents/comments/1qjkotq/what\_are\_people\_actually\_using\_for\_web\_scraping/](https://www.reddit.com/r/AI_Agents/comments/1qjkotq/what_are_people_actually_using_for_web_scraping/)  
17. Headed Playwright with WSL \- by Matt Kleinsmith \- Medium, fecha de acceso: enero 25, 2026, [https://medium.com/@matthewkleinsmith/headful-playwright-with-wsl-4bf697a44ecf](https://medium.com/@matthewkleinsmith/headful-playwright-with-wsl-4bf697a44ecf)  
18. \[SOLVED\] Force WSL GUI Apps (Playwright/Chrome) to Open on Specific Monitor with VcXsrv : r/bashonubuntuonwindows \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/bashonubuntuonwindows/comments/1mh37vq/solved\_force\_wsl\_gui\_apps\_playwrightchrome\_to/](https://www.reddit.com/r/bashonubuntuonwindows/comments/1mh37vq/solved_force_wsl_gui_apps_playwrightchrome_to/)  
19. Challenges I Faced When Displaying Playwright's Browser on WSL \- 豆蔵デベロッパーサイト, fecha de acceso: enero 25, 2026, [https://developer.mamezou-tech.com/en/blogs/2024/09/10/playwright\_headed\_wsl/](https://developer.mamezou-tech.com/en/blogs/2024/09/10/playwright_headed_wsl/)  
20. The Open-Source Web Scraping Revolution: A Deep Dive into ScrapeGraphAI, Crawl4AI, and the Future of LLM-Powered Extraction | by Tugui Dragos-Constantin \- Medium, fecha de acceso: enero 25, 2026, [https://medium.com/@tuguidragos/the-open-source-web-scraping-revolution-a-deep-dive-into-scrapegraphai-crawl4ai-and-the-future-d3a048cb448f](https://medium.com/@tuguidragos/the-open-source-web-scraping-revolution-a-deep-dive-into-scrapegraphai-crawl4ai-and-the-future-d3a048cb448f)  
21. AI Web Scraping Tools: Firecrawl & Alternatives \- Digital Marketing Agency, fecha de acceso: enero 25, 2026, [https://www.digitalapplied.com/blog/ai-web-scraping-tools-firecrawl-guide-2025](https://www.digitalapplied.com/blog/ai-web-scraping-tools-firecrawl-guide-2025)  
22. OmniParser V2: Turning Any LLM into a Computer Use Agent \- Microsoft Research, fecha de acceso: enero 25, 2026, [https://www.microsoft.com/en-us/research/articles/omniparser-v2-turning-any-llm-into-a-computer-use-agent/](https://www.microsoft.com/en-us/research/articles/omniparser-v2-turning-any-llm-into-a-computer-use-agent/)  
23. OmniParser for pure vision-based GUI agent \- Microsoft Research, fecha de acceso: enero 25, 2026, [https://www.microsoft.com/en-us/research/articles/omniparser-for-pure-vision-based-gui-agent/](https://www.microsoft.com/en-us/research/articles/omniparser-for-pure-vision-based-gui-agent/)  
24. What is the VRAM requirements ?\! · Issue \#31 · microsoft/OmniParser \- GitHub, fecha de acceso: enero 25, 2026, [https://github.com/microsoft/OmniParser/issues/31](https://github.com/microsoft/OmniParser/issues/31)  
25. CPU Offloading for Diffusion Model \- vLLM-Omni, fecha de acceso: enero 25, 2026, [https://docs.vllm.ai/projects/vllm-omni/en/latest/user\_guide/diffusion/cpu\_offload\_diffusion/](https://docs.vllm.ai/projects/vllm-omni/en/latest/user_guide/diffusion/cpu_offload_diffusion/)  
26. Run OmniParser V2 \+ OmniTool Locally With Qwen2.5VL (Zero API Costs\!) \- YouTube, fecha de acceso: enero 25, 2026, [https://www.youtube.com/watch?v=UECfiRv0XjU](https://www.youtube.com/watch?v=UECfiRv0XjU)  
27. Best OmniParser Alternatives & Competitors \- SourceForge, fecha de acceso: enero 25, 2026, [https://sourceforge.net/software/product/OmniParser/alternatives](https://sourceforge.net/software/product/OmniParser/alternatives)  
28. Best local vision models for use in "computer use" type application? : r/LocalLLaMA \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/1gbhgcx/best\_local\_vision\_models\_for\_use\_in\_computer\_use/](https://www.reddit.com/r/LocalLLaMA/comments/1gbhgcx/best_local_vision_models_for_use_in_computer_use/)  
29. Chain-of-Verification (CoVe): Reduce LLM Hallucinations \- Learn Prompting, fecha de acceso: enero 25, 2026, [https://learnprompting.org/docs/advanced/self\_criticism/chain\_of\_verification](https://learnprompting.org/docs/advanced/self_criticism/chain_of_verification)  
30. Chain-of-Verification Reduces Hallucination in Large Language Models \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/177j0gw/chainofverification\_reduces\_hallucination\_in/](https://www.reddit.com/r/LocalLLaMA/comments/177j0gw/chainofverification_reduces_hallucination_in/)  
31. Chain of Verification (CoVe) — Understanding & Implementation | by sourajit roy chowdhury | Medium, fecha de acceso: enero 25, 2026, [https://sourajit16-02-93.medium.com/chain-of-verification-cove-understanding-implementation-e7338c7f4cb5](https://sourajit16-02-93.medium.com/chain-of-verification-cove-understanding-implementation-e7338c7f4cb5)  
32. Chain of Verification Implementation Using LangChain Expression Language and LLM, fecha de acceso: enero 25, 2026, [https://www.analyticsvidhya.com/blog/2023/12/chain-of-verification-implementation-using-langchain-expression-language-and-llm/](https://www.analyticsvidhya.com/blog/2023/12/chain-of-verification-implementation-using-langchain-expression-language-and-llm/)  
33. FIRE: Fact-checking with Iterative Retrieval and Verification \- ACL Anthology, fecha de acceso: enero 25, 2026, [https://aclanthology.org/2025.findings-naacl.158.pdf](https://aclanthology.org/2025.findings-naacl.158.pdf)  
34. New resources for fact-checking LLMs presented at EMNLP \- MBZUAI, fecha de acceso: enero 25, 2026, [https://mbzuai.ac.ae/news/new-resources-for-fact-checking-llms-presented-at-emnlp/](https://mbzuai.ac.ae/news/new-resources-for-fact-checking-llms-presented-at-emnlp/)  
35. Thucy: An LLM-based Multi-Agent System for Claim Verification across Relational Databases \- arXiv, fecha de acceso: enero 25, 2026, [https://arxiv.org/html/2512.03278v1](https://arxiv.org/html/2512.03278v1)  
36. FACT-CHECKER: A WEB APPLICATION FOR LEVERAGING LARGE LANGUAGE MODELS FOR FACT-CHECKING YOUTUBE VIDEOS \- CSUSB ScholarWorks, fecha de acceso: enero 25, 2026, [https://scholarworks.lib.csusb.edu/cgi/viewcontent.cgi?article=3532\&context=etd](https://scholarworks.lib.csusb.edu/cgi/viewcontent.cgi?article=3532&context=etd)  
37. Chroma vs LanceDB | Vector Database Comparison \- Zilliz, fecha de acceso: enero 25, 2026, [https://zilliz.com/comparison/chroma-vs-lancedb](https://zilliz.com/comparison/chroma-vs-lancedb)  
38. LanceDB vs. Chroma vs. pgvector Comparison \- SourceForge, fecha de acceso: enero 25, 2026, [https://sourceforge.net/software/compare/LanceDB-vs-chroma-vs-pgvector/](https://sourceforge.net/software/compare/LanceDB-vs-chroma-vs-pgvector/)  
39. AnythingLLM's Competitive Edge: LanceDB for Seamless RAG and Agent Workflows, fecha de acceso: enero 25, 2026, [https://lancedb.com/blog/anythingllms-competitive-edge-lancedb-for-seamless-rag-and-agent-workflows/](https://lancedb.com/blog/anythingllms-competitive-edge-lancedb-for-seamless-rag-and-agent-workflows/)  
40. The LanceDB Administrator's Handbook: A Comprehensive Tutorial on Live Database Manipulation and Management \- Fahad Siddique Faisal, fecha de acceso: enero 25, 2026, [https://fahadsid1770.medium.com/the-lancedb-administrators-handbook-a-comprehensive-tutorial-on-live-database-manipulation-and-5e6915727898?source=rss------artificial\_intelligence-5](https://fahadsid1770.medium.com/the-lancedb-administrators-handbook-a-comprehensive-tutorial-on-live-database-manipulation-and-5e6915727898?source=rss------artificial_intelligence-5)  
41. LanceDB | Vector Database for RAG, Agents & Hybrid Search, fecha de acceso: enero 25, 2026, [https://lancedb.com/](https://lancedb.com/)  
42. LanceDB \- LanceDB, fecha de acceso: enero 25, 2026, [https://docs.lancedb.com/](https://docs.lancedb.com/)  
43. Example RO-Crates \- Research Object, fecha de acceso: enero 25, 2026, [https://www.researchobject.org/ro-crate/examples](https://www.researchobject.org/ro-crate/examples)  
44. 2021-packaging-research-artefacts-with-ro-crate/ro-crate-metadata.json at main \- GitHub, fecha de acceso: enero 25, 2026, [https://github.com/ResearchObject/2021-packaging-research-artefacts-with-ro-crate/blob/main/ro-crate-metadata.json](https://github.com/ResearchObject/2021-packaging-research-artefacts-with-ro-crate/blob/main/ro-crate-metadata.json)  
45. APPENDIX: RO-Crate JSON-LD \- Research Object, fecha de acceso: enero 25, 2026, [https://www.researchobject.org/ro-crate/specification/1.1/appendix/jsonld.html](https://www.researchobject.org/ro-crate/specification/1.1/appendix/jsonld.html)  
46. RO-Crate: A framework for packaging research products into FAIR Research Objects, fecha de acceso: enero 25, 2026, [https://www.rd-alliance.org/wp-content/uploads/2024/05/2021-02-25-ro-crate-fdo-FINAL.pdf](https://www.rd-alliance.org/wp-content/uploads/2024/05/2021-02-25-ro-crate-fdo-FINAL.pdf)  
47. 5 Minute beginner tutorial: Describo and Research Object Crates (RO-Crate), fecha de acceso: enero 25, 2026, [https://describo.github.io/docs/guide/five-minute-tutorial.html](https://describo.github.io/docs/guide/five-minute-tutorial.html)  
48. Improving low VRAM performance for dense models using MoE offload technique \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/1o8jocc/improving\_low\_vram\_performance\_for\_dense\_models/](https://www.reddit.com/r/LocalLLaMA/comments/1o8jocc/improving_low_vram_performance_for_dense_models/)  
49. Quantizing 70b models to 4-bit, how much does performance degrade? \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/185036z/quantizing\_70b\_models\_to\_4bit\_how\_much\_does/](https://www.reddit.com/r/LocalLLaMA/comments/185036z/quantizing_70b_models_to_4bit_how_much_does/)  
50. Running a local model with 8GB VRAM \- Is it even remotely possible? : r/LocalLLaMA \- Reddit, fecha de acceso: enero 25, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/19f9z64/running\_a\_local\_model\_with\_8gb\_vram\_is\_it\_even/](https://www.reddit.com/r/LocalLLaMA/comments/19f9z64/running_a_local_model_with_8gb_vram_is_it_even/)