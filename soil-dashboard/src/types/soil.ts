export type SoilReading = {
  t: number
  moisture: number
  tempC: number
  ecMicroSiemens: number
  ph: number
  nitrogenMgKg: number
}

export type SoilPayload = {
  source: string
  notes: {
    locations: [string, string]
  }
  series: {
    huntsville: SoilReading[]
    uncc: SoilReading[]
  }
}

export type MergedByTime = {
  t: number
  huntsvilleMoisture: number
  unccMoisture: number
  huntsvilleEc: number
  unccEc: number
  huntsvillePh: number
  unccPh: number
  huntsvilleTemp: number
  unccTemp: number
  huntsvilleN: number
  unccN: number
}
