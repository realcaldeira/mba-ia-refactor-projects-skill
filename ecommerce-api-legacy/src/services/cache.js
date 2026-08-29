'use strict';

/**
 * Cache com limite e TTL, instanciado e injetado.
 * Substitui o objeto de módulo `globalCache`, que crescia sem limite pelo tempo de vida do processo.
 */
class Cache {
  constructor({ maxEntradas = 500, ttlMs = 60_000 } = {}) {
    this.maxEntradas = maxEntradas;
    this.ttlMs = ttlMs;
    this.mapa = new Map();
  }

  set(chave, valor) {
    if (this.mapa.size >= this.maxEntradas) {
      this.mapa.delete(this.mapa.keys().next().value);
    }
    this.mapa.set(chave, { valor, expiraEm: Date.now() + this.ttlMs });
  }

  get(chave) {
    const entrada = this.mapa.get(chave);
    if (!entrada) return undefined;
    if (entrada.expiraEm < Date.now()) {
      this.mapa.delete(chave);
      return undefined;
    }
    return entrada.valor;
  }

  get tamanho() {
    return this.mapa.size;
  }
}

module.exports = { Cache };
