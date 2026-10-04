// Textos de las pantallas de Noor, en el mismo idioma que la voz.
// Quechua: BORRADOR DEL EQUIPO, SIN VALIDAR por un hablante nativo. Se armó con las frases de audio/mensajes.json
// (también borrador). La tabla para revisarlo está en docs/TEXTOS_PANTALLA.md: si cambia algo allí, cambia aquí.
// Regla de oro: ningún texto lleva cifras (lo vigila ui/sin-cifras.test.tsx en los dos idiomas).
import { createContext, useContext } from 'react';

export type Idioma = 'es' | 'quz';

const ES = {
  idioma: 'Castellano',
  cambiarIdioma: 'Idioma: castellano. Tocar para cambiar a quechua',
  escuchar: 'Escuchar',
  fotoTrampa: 'Que se vean las cuatro esquinas',
  fotoHojas: 'Hojas volteadas',
  fotoOtraVez: 'Otra vez, con más luz',
  tomarFoto: 'Tomar foto',
  contando: 'Contando',
  preguntaGranos: '¿Granos con huequito?',
  preguntaPolvo: '¿Polvo naranja debajo?',
  sanos: 'Sanos',
  pocos: 'Pocos con huequito',
  muchos: 'Muchos con huequito',
  noSe: 'No sé',
  siPolvo: 'Sí, hay polvo',
  noPolvo: 'No hay',
  estadoVerde: 'Todo bien',
  estadoAmarillo: 'Atención',
  estadoTecnico: 'El técnico lo verá',
  estadoUrgente: 'Aviso al técnico',
  accionBroca: 'Recoge los granos caídos',
  accionRoya: 'Puede ser roya',
  accionClima: 'Fue el clima',
  accionVerde: 'Sigue cuidando tu chacra',
  accionTecnico: 'Ya le mandé tu caso',
  llegoTecnico: 'Ya le llegó al técnico',
  guardadoSinSenal: 'Guardado. Le llegará al técnico cuando haya señal',
  yaLoHice: 'Ya lo hice',
  muyBien: '¡Muy bien!',
  terminar: 'Terminar',
  todoEnviado: 'Todo enviado',
  seEnviara: 'Guardado; se enviará con señal',
};

export type Textos = typeof ES;

const QUZ: Textos = {
  idioma: 'Runasimi',
  cambiarIdioma: 'Simi: runasimi. Ñit\'iy castellanoman tikranapaq',
  escuchar: 'Uyariy',
  fotoTrampa: 'Tawantin k\'uchukuna rikhurichun',
  fotoHojas: 'Kimsa raphita tikray',
  fotoOtraVez: 'Watiqmanta, aswan k\'anchaypi',
  tomarFoto: 'Fotota hurquy',
  contando: 'Yupashani',
  preguntaGranos: '¿T\'uquyuq rurukuna?',
  preguntaPolvo: '¿Uranpi naranha ñut\'u kanchu?',
  sanos: 'Qhali',
  pocos: 'Pisi t\'uquyuq',
  muchos: 'Achka t\'uquyuq',
  noSe: 'Mana yachanichu',
  siPolvo: 'Arí, kanmi',
  noPolvo: 'Manam kanchu',
  estadoVerde: 'Tukuy allin',
  estadoAmarillo: '¡Qhawariy!',
  estadoTecnico: 'Técnicon qhawanqa',
  estadoUrgente: 'Técnicoman willasqa',
  accionBroca: 'Urmasqa rurukunata pallay',
  accionRoya: 'Royachá kanman',
  accionClima: 'Timpun karqan',
  accionVerde: 'Hinallata qhawarillay',
  accionTecnico: 'Casoykita apachiniña',
  llegoTecnico: 'Técnicomanña chayan',
  guardadoSinSenal: 'Waqaychasqa. Señal kaqtin técnicoman chayanqa',
  yaLoHice: 'Ruwaniña',
  muyBien: '¡Allinmi!',
  terminar: 'Tukuchiy',
  todoEnviado: 'Tukuy apachisqa',
  seEnviara: 'Waqaychasqa; señal kaqtin apachikunqa',
};

export const TEXTOS: Record<Idioma, Textos> = { es: ES, quz: QUZ };

/** El idioma elegido con el botón de la barra: manda en la voz y en la pantalla. */
export const IdiomaContexto = createContext<Idioma>('es');
export const useTextos = (): Textos => TEXTOS[useContext(IdiomaContexto)];
