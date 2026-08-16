import subprocess
import os
import json
import re
import time
from urllib.parse import urlparse

def get_direct_url(video_url):
    """
    Extrae la URL directa del video usando yt-dlp
    Soporta: OK.ru, Videa.hu, TokyoVideo, VKVideo
    """
    try:
        # Limpiar URL
        video_url = video_url.strip()
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        elif not video_url.startswith(('http://', 'https://')):
            video_url = 'https://' + video_url
        
        # Detectar plataforma
        plataforma = None
        if 'ok.ru' in video_url:
            plataforma = 'ok.ru'
        elif 'vkvideo.ru' in video_url or 'vk.com' in video_url:
            plataforma = 'vkvideo.ru'
        elif 'videa.hu' in video_url:
            plataforma = 'videa.hu'
        elif 'tokyvideo.com' in video_url:
            plataforma = 'tokyvideo.com'
        
        if not plataforma:
            print(f"   ⚠️ Plataforma no soportada: {video_url[:50]}...")
            return None
        
        print(f"   🔍 Plataforma detectada: {plataforma}")
        
        # Comando yt-dlp - usar -g para obtener solo la URL directa
        cmd = ['yt-dlp', '-g', video_url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        
        if result.returncode == 0 and result.stdout.strip():
            url_directa = result.stdout.strip()
            print(f"   ✅ URL directa obtenida: {url_directa[:80]}...")
            return url_directa
        
        print(f"   ❌ Falló la extracción para {plataforma}")
        return None
        
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout al extraer URL")
        return None
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
        return None

def procesar_pelicula(pelicula, idx, total):
    """Procesa una película individual"""
    titulo = pelicula.get('TITULO', f'Película {idx+1}')
    urls = pelicula.get('URLS', pelicula.get('URLS_OKRU', []))
    id_video = pelicula.get('ID_VIDEO', pelicula.get('ID_OKRU'))
    categoria = pelicula.get('CATEGORIA', 'GENERAL').upper()
    plataforma = pelicula.get('PLATAFORMA', 'desconocida')
    
    if not urls:
        print(f"⚠️ [{idx+1}/{total}] {titulo} - Sin URLs")
        return pelicula
    
    print(f"🔄 [{idx+1}/{total}] [{categoria}] {titulo} - ID: {id_video} - {plataforma}")
    
    # Tomar la primera URL
    url_video = urls[0]
    
    # Obtener URL directa
    url_directa = get_direct_url(url_video)
    
    if url_directa:
        pelicula['URL_DIRECTA'] = url_directa
        print(f"   ✅ URL_DIRECTA obtenida")
    else:
        pelicula['URL_DIRECTA'] = ""
        print(f"   ❌ Falló la extracción - URL no disponible temporalmente")
    
    return pelicula

def main():
    print("="*70)
    print("🎬 EXTRACTOR MULTI-PLATAFORMA - OKRU-PROMAX3")
    print("   Soporta: OK.ru | Videa.hu | TokyoVideo | VKVideo")
    print("   🔒 urls.txt es la BASE DE DATOS - NUNCA se limpia")
    print("="*70)
    
    # 1. Verificar urls.txt - SIEMPRE DEBE EXISTIR
    if not os.path.exists('urls.txt'):
        print("📝 Creando urls.txt vacío...")
        with open('urls.txt', 'w', encoding='utf-8') as f:
            f.write("[]")
        print("ℹ️ urls.txt creado. Agrega películas desde la interfaz gráfica.")
        return
    
    # 2. Leer TODAS las películas desde urls.txt
    with open('urls.txt', 'r', encoding='utf-8') as f:
        contenido = f.read().strip()
    
    if not contenido or contenido == "[]":
        print("ℹ️ urls.txt está vacío. Agrega películas desde la interfaz gráfica.")
        return
    
    try:
        peliculas = json.loads(contenido)
    except json.JSONDecodeError as e:
        print(f"❌ urls.txt no contiene JSON válido: {e}")
        return
    
    print(f"📥 {len(peliculas)} películas encontradas en urls.txt")
    
    # 3. Crear directorios
    os.makedirs('peliculas', exist_ok=True)
    
    # 4. Procesar CADA película
    peliculas_procesadas = 0
    peliculas_con_error = 0
    
    for i, pelicula in enumerate(peliculas):
        pelicula_procesada = procesar_pelicula(pelicula, i, len(peliculas))
        
        # ACTUALIZAR urls.txt EN VIVO - NUNCA LIMPIAR
        peliculas[i] = pelicula_procesada
        with open('urls.txt', 'w', encoding='utf-8') as f:
            json.dump(peliculas, f, indent=2, ensure_ascii=False)
        
        if pelicula_procesada.get('URL_DIRECTA'):
            peliculas_procesadas += 1
        else:
            peliculas_con_error += 1
        
        time.sleep(0.3)
    
    # 5. ORGANIZAR POR CATEGORÍA en /peliculas/
    categorias_dict = {}
    for pelicula in peliculas:
        categoria = pelicula.get('CATEGORIA', 'GENERAL').upper()
        if categoria not in categorias_dict:
            categorias_dict[categoria] = []
        categorias_dict[categoria].append(pelicula)
    
    # 6. Guardar en archivos por categoría
    for categoria, pelis in categorias_dict.items():
        json_path = os.path.join('peliculas', f'{categoria}.json')
        
        # Cargar JSON existente de esa categoría
        data = []
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = []
        
        # Actualizar o agregar (por ID)
        for pelicula in pelis:
            id_busqueda = pelicula.get('ID_VIDEO') or pelicula.get('ID_OKRU') or pelicula.get('TMDB_ID')
            encontrado = False
            for j, item in enumerate(data):
                item_id = item.get('ID_VIDEO') or item.get('ID_OKRU') or item.get('TMDB_ID')
                if item_id == id_busqueda or item.get('TMDB_ID') == pelicula.get('TMDB_ID'):
                    data[j] = pelicula
                    encontrado = True
                    break
            if not encontrado:
                data.append(pelicula)
        
        # Guardar JSON de categoría
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"   📁 {categoria}.json → {len(data)} películas")
    
    # 7. Actualizar category_list.json
    with open('category_list.json', 'w', encoding='utf-8') as f:
        json.dump(list(categorias_dict.keys()), f, indent=2, ensure_ascii=False)
    
    # 8. NUNCA LIMPIAR urls.txt - ES LA BASE DE DATOS
    print(f"\n🔒 urls.txt conserva {len(peliculas)} películas - BASE DE DATOS PRINCIPAL")
    
    print("\n" + "="*70)
    print(f"🎉 Proceso completado")
    print(f"✅ {peliculas_procesadas} películas con URL directa")
    print(f"⚠️ {peliculas_con_error} películas sin URL directa (reintentar después)")
    print(f"📂 Categorías creadas: {list(categorias_dict.keys())}")
    print("🔒 urls.txt NO fue eliminado - Contiene TODOS los datos")
    print("="*70)

if __name__ == "__main__":
    main()
