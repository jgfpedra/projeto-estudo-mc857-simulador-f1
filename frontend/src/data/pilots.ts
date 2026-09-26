export const NULL_DRIVER_ID = "__null_driver__"

export type Driver = {
  id: string
  name: string
  shortName: string
  number: number
  nationality: string
  countryCode: string
  teamId: string
  teamName: string
}

export const NULL_DRIVER: Driver = {
  id: NULL_DRIVER_ID,
  name: "Nenhum piloto",
  shortName: "VAZIO",
  number: 0,
  nationality: "—",
  countryCode: "",
  teamId: "",
  teamName: "Piloto nulo",
}

export const pilots: Driver[] = [
  { id: "leclerc", name: "Charles Leclerc", shortName: "LEC", number: 16, nationality: "Mônaco", countryCode: "MC", teamId: "red", teamName: "Scuderia Ferrari" },
  { id: "hamilton", name: "Lewis Hamilton", shortName: "HAM", number: 44, nationality: "Reino Unido", countryCode: "GB", teamId: "red", teamName: "Scuderia Ferrari" },
  { id: "russell", name: "George Russell", shortName: "RUS", number: 63, nationality: "Reino Unido", countryCode: "GB", teamId: "mercedes", teamName: "Mercedes-AMG" },
  { id: "antonelli", name: "Kimi Antonelli", shortName: "ANT", number: 12, nationality: "Itália", countryCode: "IT", teamId: "mercedes", teamName: "Mercedes-AMG" },
  { id: "norris", name: "Lando Norris", shortName: "NOR", number: 4, nationality: "Reino Unido", countryCode: "GB", teamId: "mclaren", teamName: "McLaren Racing" },
  { id: "piastri", name: "Oscar Piastri", shortName: "PIA", number: 81, nationality: "Austrália", countryCode: "AU", teamId: "mclaren", teamName: "McLaren Racing" },
  { id: "verstappen", name: "Max Verstappen", shortName: "VER", number: 3, nationality: "Países Baixos", countryCode: "NL", teamId: "redbull", teamName: "Red Bull Racing" },
  { id: "tsunoda", name: "Yuki Tsunoda", shortName: "TSU", number: 22, nationality: "Japão", countryCode: "JP", teamId: "redbull", teamName: "Red Bull Racing" },
  { id: "alonso", name: "Fernando Alonso", shortName: "ALO", number: 14, nationality: "Espanha", countryCode: "ES", teamId: "aston", teamName: "Aston Martin" },
  { id: "stroll", name: "Lance Stroll", shortName: "STR", number: 18, nationality: "Canadá", countryCode: "CA", teamId: "aston", teamName: "Aston Martin" },
  { id: "gasly", name: "Pierre Gasly", shortName: "GAS", number: 10, nationality: "França", countryCode: "FR", teamId: "alpine", teamName: "Alpine F1 Team" },
  { id: "colapinto", name: "Franco Colapinto", shortName: "COL", number: 43, nationality: "Argentina", countryCode: "AR", teamId: "alpine", teamName: "Alpine F1 Team" },
  { id: "albon", name: "Alexander Albon", shortName: "ALB", number: 23, nationality: "Tailândia", countryCode: "TH", teamId: "williams", teamName: "Williams Racing" },
  { id: "sainz", name: "Carlos Sainz", shortName: "SAI", number: 55, nationality: "Espanha", countryCode: "ES", teamId: "williams", teamName: "Williams Racing" },
  { id: "hulkenberg", name: "Nico Hülkenberg", shortName: "HUL", number: 27, nationality: "Alemanha", countryCode: "DE", teamId: "sauber", teamName: "Sauber" },
  { id: "bortoleto", name: "Gabriel Bortoleto", shortName: "BOR", number: 5, nationality: "Brasil", countryCode: "BR", teamId: "sauber", teamName: "Sauber" },
  { id: "lawson", name: "Liam Lawson", shortName: "LAW", number: 30, nationality: "Nova Zelândia", countryCode: "NZ", teamId: "rb", teamName: "Racing Bulls" },
  { id: "hadjar", name: "Isack Hadjar", shortName: "HAD", number: 6, nationality: "França", countryCode: "FR", teamId: "rb", teamName: "Racing Bulls" },
  { id: "ocon", name: "Esteban Ocon", shortName: "OCO", number: 31, nationality: "França", countryCode: "FR", teamId: "haas", teamName: "Haas F1 Team" },
  { id: "bearman", name: "Oliver Bearman", shortName: "BEA", number: 87, nationality: "Reino Unido", countryCode: "GB", teamId: "haas", teamName: "Haas F1 Team" },
]

export function getDriverById(driverId: string): Driver {
  if (driverId === NULL_DRIVER_ID) return NULL_DRIVER
  return pilots.find((pilot) => pilot.id === driverId) ?? NULL_DRIVER
}

export function flag(countryCode: string) {
  if (!countryCode) return ""
  return countryCode
    .toUpperCase()
    .replace(/./g, (char) => String.fromCodePoint(127397 + char.charCodeAt(0)))
}
