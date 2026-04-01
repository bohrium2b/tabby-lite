import type {Round, RoundDraw} from "../types/round.ts";
import axios from "axios";

export const getRounds = (): Promise<Round[]> => {
  // Get all rounds from the API
  return axios.get("/api/rounds/").then(response => response.data);
};


export const getRound = (roundId: number): Promise<Round> => {
  // Get a specific round from the API
  return axios.get(`/api/rounds/${roundId}/`).then(response => response.data);
}


export const getDraw = (roundId: number): Promise<RoundDraw> => {
  // Get the draw for a specific round from the API
  return axios.get(`/api/rounds/${roundId}/draw/`).then(response => response.data);
}