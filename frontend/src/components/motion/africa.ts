/**
 * Géométrie simplifiée de l'Afrique pour une carte en matrice de points.
 * Contour approximatif (longitude, latitude), volontairement grossier : l'objectif
 * est graphique, pas cartographique.
 */

type LonLat = [number, number];

const MAINLAND: LonLat[] = [
  [-5.8, 35.8], [3, 36.8], [10.2, 37], [11, 37.1], [10, 34], [13, 32.9], [16.6, 31.2],
  [20, 32.1], [24, 32], [29.9, 31.2], [32.3, 31.3], [32.5, 29.9], [34, 27], [37.2, 19.6],
  [39.5, 15.5], [43.1, 11.6], [51.2, 11.8], [51.3, 10.4], [48, 5], [45.3, 2], [42.5, -0.4],
  [39.7, -4], [39.3, -6.8], [40.5, -10.5], [40.7, -15], [34.8, -19.8], [35.5, -22], [32.6, -26],
  [31, -29.9], [27.9, -33], [25.6, -34], [20, -34.8], [18.4, -34], [15, -27], [14.5, -22.9],
  [11.8, -17.3], [13.2, -8.8], [12.3, -6], [9.3, -1], [9.7, 4], [6, 4.3], [3.4, 6.4],
  [-0.2, 5.6], [-4, 5.3], [-7.7, 4.4], [-10.8, 6.3], [-13.2, 8.5], [-13.7, 9.5], [-15.6, 11.9],
  [-17.4, 14.7], [-16.5, 16], [-16, 18.1], [-17, 20.8], [-15.9, 23.7], [-12.9, 27.9],
  [-9.6, 30.4], [-7.6, 33.6], [-6.8, 34],
];

const MADAGASCAR: LonLat[] = [
  [49.3, -12], [50.5, -15.5], [47, -25], [44, -25], [43.3, -22], [44.5, -16], [47, -13.5],
];

export const VIEW_WIDTH = 100;
export const VIEW_HEIGHT = 104;

/** Projection équirectangulaire dans un repère 100 × 104. */
export function project([lon, lat]: LonLat): [number, number] {
  return [((lon + 20) / 74) * VIEW_WIDTH, ((38.5 - lat) / 75) * VIEW_HEIGHT];
}

function inside([x, y]: LonLat, polygon: LonLat[]): boolean {
  let result = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      result = !result;
    }
  }
  return result;
}

/** Points de la grille situés sur le continent (calculés une seule fois). */
export const DOTS: [number, number][] = (() => {
  const dots: [number, number][] = [];
  const step = 1.55;
  for (let lat = 37.5; lat > -36; lat -= step) {
    for (let lon = -18.5; lon < 52.5; lon += step) {
      const point: LonLat = [lon, lat];
      if (inside(point, MAINLAND) || inside(point, MADAGASCAR)) {
        dots.push(project(point));
      }
    }
  }
  return dots;
})();

export interface City {
  name: string;
  at: [number, number];
}

const CITY_COORDS: Record<string, LonLat> = {
  Dakar: [-17.4, 14.7],
  Abidjan: [-4, 5.3],
  Lagos: [3.4, 6.4],
  Accra: [-0.2, 5.6],
  Bamako: [-8, 12.6],
  Kinshasa: [15.3, -4.3],
  Nairobi: [36.8, -1.3],
  "Addis-Abeba": [38.7, 9],
  "Le Caire": [31.2, 30],
  Casablanca: [-7.6, 33.6],
  Johannesburg: [28, -26.2],
  Kigali: [30, -1.9],
  Cotonou: [2.4, 6.4],
  Antananarivo: [47.5, -18.9],
};

export const CITIES: City[] = Object.entries(CITY_COORDS).map(([name, coords]) => ({ name, at: project(coords) }));

const LINKS: [string, string][] = [
  ["Dakar", "Lagos"],
  ["Abidjan", "Nairobi"],
  ["Casablanca", "Dakar"],
  ["Lagos", "Kinshasa"],
  ["Le Caire", "Addis-Abeba"],
  ["Nairobi", "Johannesburg"],
  ["Kigali", "Cotonou"],
  ["Bamako", "Le Caire"],
  ["Accra", "Johannesburg"],
  ["Nairobi", "Antananarivo"],
];

/** Arcs courbes entre villes (courbe de Bézier quadratique bombée vers le haut). */
export const ARCS = LINKS.map(([from, to]) => {
  const [x1, y1] = CITIES.find((city) => city.name === from)!.at;
  const [x2, y2] = CITIES.find((city) => city.name === to)!.at;
  const distance = Math.hypot(x2 - x1, y2 - y1);
  const cx = (x1 + x2) / 2;
  const cy = (y1 + y2) / 2 - distance * 0.35;
  return { id: `${from}-${to}`, d: `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}` };
});
