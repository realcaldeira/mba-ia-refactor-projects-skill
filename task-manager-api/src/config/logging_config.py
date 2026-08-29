"""Logging estruturado — substitui os prints espalhados pelas rotas."""
import logging


def configurar_logging(nivel="INFO"):
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )
    return logging.getLogger("taskmanager")
