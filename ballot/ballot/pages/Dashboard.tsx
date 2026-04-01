import React, { useEffect } from "react"
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getRounds } from "@/lib/api";
import type { Round } from "@/types/round";
import { Button } from "@/components/ui/button";

export const Dashboard = () => {
    const [rounds, setRounds] = React.useState<Round[] | null>([]);

    useEffect(() => {
        const fetchRounds = async () => {
            const roundsData = await getRounds();
            setRounds(roundsData);
        };

        fetchRounds();
    }, []);

    return (
        <div className="p-8">
            <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
            <p className="text-lg text-slate-700 dark:text-slate-300">
                Welcome to the Ballot dashboard! Here you can manage your tournaments and submit ballots.
            </p>
            <div className="mt-8">
                <h2 className="text-2xl font-semibold mb-4">Current Rounds</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                    {rounds && rounds.length > 0 && Array.isArray(rounds) ? (
                        rounds.map((round) => (
                            <Card key={round.id}>
                                <CardHeader>
                                    <CardTitle>{round.name}</CardTitle>
                                    <Badge variant="outline">{round.completed ? "Completed" : "In Progress"}</Badge>
                                </CardHeader>
                            </Card>
                        ))
                    ) : (
                        <p className="text-slate-500">No rounds available.</p>
                    )}
                </div>
            </div>
        </div>
     )
}
