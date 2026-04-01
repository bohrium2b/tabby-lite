export type Round = {
    id: number;
    name: string;
    completed: boolean;
    motions: Motion[];
};


export type Motion = {
    id: number;
    text: string;
    info_slide?: string;
    reference?: string;
}


export type RoundDraw = DrawPairing[];

export type DrawPairing = {
    id: number;
    venue: Venue;
    teams: DrawTeam[];
    adjudicators: {
        chair: Adjudicator;
        panellists: Adjudicator[];
        trainees: Adjudicator[];
    };
}


export type DrawTeam = {
    team: Team;
    side: "aff" | "neg";
}


export type Team = {
    id: number;
    short_name: string;
    long_name: string;
    code_name: string;
    speakers: Speaker[];
    emoji: string | null;
    short_reference: string;
    reference: string;
}


export type Speaker = {
    id: number;
    name: string;
    email: string | null;
}


export type Adjudicator = {
    id: number;
    name: string;
    email: string | null;
};


export type Venue = {
    id: number;
    name: string;
}