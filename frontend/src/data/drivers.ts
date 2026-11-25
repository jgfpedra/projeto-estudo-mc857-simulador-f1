import type { Driver } from "@/types/driver"

// Mock temporário baseado na lista que já existia em DriverTeamSelection.
// A API deverá retornar os pilotos da temporada solicitada.
export const driversBySeason: Record<number, Driver[]> = {
  2025: [
    { id: "leclerc", name: "Charles Leclerc", shortName: "LEC", number: 16, country: "Mônaco", countryCode: "MC", teamId: "ferrari", teamName: "Scuderia Ferrari", teamShortName: "Ferrari" },
    { id: "hamilton", name: "Lewis Hamilton", shortName: "HAM", number: 44, country: "Reino Unido", countryCode: "GB", teamId: "ferrari", teamName: "Scuderia Ferrari", teamShortName: "Ferrari" },
    { id: "russell", name: "George Russell", shortName: "RUS", number: 63, country: "Reino Unido", countryCode: "GB", teamId: "mercedes", teamName: "Mercedes-AMG", teamShortName: "Mercedes" },
    { id: "antonelli", name: "Kimi Antonelli", shortName: "ANT", number: 12, country: "Itália", countryCode: "IT", teamId: "mercedes", teamName: "Mercedes-AMG", teamShortName: "Mercedes" },
    { id: "norris", name: "Lando Norris", shortName: "NOR", number: 4, country: "Reino Unido", countryCode: "GB", teamId: "mclaren", teamName: "McLaren Racing", teamShortName: "McLaren" },
    { id: "piastri", name: "Oscar Piastri", shortName: "PIA", number: 81, country: "Austrália", countryCode: "AU", teamId: "mclaren", teamName: "McLaren Racing", teamShortName: "McLaren" },
    { id: "verstappen", name: "Max Verstappen", shortName: "VER", number: 3, country: "Países Baixos", countryCode: "NL", teamId: "redbull", teamName: "Red Bull Racing", teamShortName: "Red Bull" },
    { id: "tsunoda", name: "Yuki Tsunoda", shortName: "TSU", number: 22, country: "Japão", countryCode: "JP", teamId: "redbull", teamName: "Red Bull Racing", teamShortName: "Red Bull" },
    { id: "alonso", name: "Fernando Alonso", shortName: "ALO", number: 14, country: "Espanha", countryCode: "ES", teamId: "aston", teamName: "Aston Martin", teamShortName: "Aston Martin" },
    { id: "stroll", name: "Lance Stroll", shortName: "STR", number: 18, country: "Canadá", countryCode: "CA", teamId: "aston", teamName: "Aston Martin", teamShortName: "Aston Martin" },
    { id: "gasly", name: "Pierre Gasly", shortName: "GAS", number: 10, country: "França", countryCode: "FR", teamId: "alpine", teamName: "Alpine F1 Team", teamShortName: "Alpine" },
    { id: "colapinto", name: "Franco Colapinto", shortName: "COL", number: 43, country: "Argentina", countryCode: "AR", teamId: "alpine", teamName: "Alpine F1 Team", teamShortName: "Alpine" },
    { id: "albon", name: "Alexander Albon", shortName: "ALB", number: 23, country: "Tailândia", countryCode: "TH", teamId: "williams", teamName: "Williams Racing", teamShortName: "Williams" },
    { id: "sainz", name: "Carlos Sainz", shortName: "SAI", number: 55, country: "Espanha", countryCode: "ES", teamId: "williams", teamName: "Williams Racing", teamShortName: "Williams" },
    { id: "hulkenberg", name: "Nico Hülkenberg", shortName: "HUL", number: 27, country: "Alemanha", countryCode: "DE", teamId: "sauber", teamName: "Sauber", teamShortName: "Sauber" },
    { id: "bortoleto", name: "Gabriel Bortoleto", shortName: "BOR", number: 5, country: "Brasil", countryCode: "BR", teamId: "sauber", teamName: "Sauber", teamShortName: "Sauber" },
    { id: "lawson", name: "Liam Lawson", shortName: "LAW", number: 30, country: "Nova Zelândia", countryCode: "NZ", teamId: "rb", teamName: "Racing Bulls", teamShortName: "RB" },
    { id: "hadjar", name: "Isack Hadjar", shortName: "HAD", number: 6, country: "França", countryCode: "FR", teamId: "rb", teamName: "Racing Bulls", teamShortName: "RB" },
    { id: "ocon", name: "Esteban Ocon", shortName: "OCO", number: 31, country: "França", countryCode: "FR", teamId: "haas", teamName: "Haas F1 Team", teamShortName: "Haas" },
    { id: "bearman", name: "Oliver Bearman", shortName: "BEA", number: 87, country: "Reino Unido", countryCode: "GB", teamId: "haas", teamName: "Haas F1 Team", teamShortName: "Haas" },
  ],
}
